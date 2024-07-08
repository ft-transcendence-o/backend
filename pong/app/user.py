from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.core.cache import cache
from urllib.parse import urlencode
from os import getenv
import pyotp
import requests
import jwt

from app.decorators import login_required

"""
42 OAuth2의 흐름
1. https://api.intra.42.fr/oauth/authorize 사용자를 연결한다.
2. 사용자가 권한을 부여하는 화면이 반환된다.
3. 제공된 client_id를 포함한 authorize URL을 사용한다.
4. 사용자가 권한을 부여하는경우, redirect uri로 리다이렉션 되며, "code"를 반환한다.
5. https://api.intra.42.fr/oauth/token URI에 POST요청으로
    { client_id, client_secret, code, redirect_uri }
    인자를 넘겨준다. 서버 측에서 보안 연결을 통해 수행되야 한다.
6. 받은 "code"를 활용하여 /oauth/token URI를 통해 access_token 을 반환받는다.
7. access_token을 header에 추가하여 API request를 구성한다.
    curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" /
        https://api.intra.42.fr/v2/me
"""

"""
backend 인증 로직
1. frontend에서 redirectURI를 통하여 얻은 "code"를 받는다
2. "code"를 access_token으로 exchange한다.
3. access_token을 사용하여 /v2/me 에서 정보를 받는다.
4. email 정보를 사용하여 2FA를 실행한다
5. 첫번째 로그인의 경우 OTP에 필요한 secret을 생성하고 
    URI로 QR code를 그린다
6. QR code를 사용해 google authenticator 등록
7. OTP 입력 및 검증
"""

API_URL = getenv("API_URL")

"""
OTP 주의사항
1. HTTPS 통신 사용
2. OTP브루트포스 방지 (타임스탬프 확인)
3. 스로틀 속도 제한
"""

# @login_required
def otp_test(request):
    """
    otp URI를 만들고 이를 QRcode로 변환하여 사용
    secret key 값을 user db에 저장한 뒤 꺼내어서 사용
    :request secret: pyotp secret of user info
    """
    secret = pyotp.random_base32()
    URI = pyotp.totp.TOTP(secret).provisioning_uri(
        # TODO: user email로 입력
        name="user@mail.com", issuer_name="pong_game"
    )
    # TODO: need to store secret value in user db
    return JsonResponse({"otpauth_uri": URI}, status=200)


# @login_required
def validate_otp(request):
    """
    user의 secret값을 사용해서 otp 값이 타당한지 확인
    secret을 db에서 매번 확인하는 것, caching 하는 것 선택
    """
    # TODO: db? caching?
    secret = "temp"
    input_pass = request.POST.get("otp")
    expected_pass = pyotp.TOTP(secret).now() # type str
    if input_pass != expected_pass:
        return HttpResponse("bad")
    return HttpResponse("good")
    

@login_required
def need_login(request):
    return HttpResponse("Can you join")

def get_user_info(request):
    """
    access_token을 활용하여 user의 정보를 받아온다.
    """
    URI = API_URL + "/v2/me"
    token = "81a462114352aa75674c78cf816567ad802858724b3494f524f274532ab2cc24"
    headers = { "Authorization": "Bearer %s" % token }
    response = requests.get(URI, headers=headers)
    return HttpResponse(response.text)


def get_token_info(request):
    """
    access_token을 발급 받고 테스트
    expired 및 status_code를 사용해 유효한지 확인
    :request jwt: acces_token이 담긴 jwt
    """
    URI = API_URL + "/auth/token/info"
    encoded_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NfdG9rZW4iOiI0MjQyYjk1YWY4MzBiNzI1MjllZmJkZTA2MDI5OTAxYWEyZTA4YmY3ZDRlYmMzMzIwYjI1ZmIzNGUyMjllZWFhIn0.eIivOHCPQVxtIouADQss3re6yrlSlWtCycGCUKss4QE"
    JWT_SECRET = getenv("JWT_SECRET")
    decoded_jwt = jwt.decode(encoded_jwt, JWT_SECRET, algorithms=["HS256"])
    token = decoded_jwt.get("access_token")
    headers = { "Authorization": "Bearer %s" % token }
    response = requests.get(URI, headers=headers)
    return HttpResponse(response.text)


def temp_access_token(request):
    """
    테스트용 grant_type == client_credentials
    """
    INTRA_UID = getenv("INTRA_UID")
    INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
    URI = API_URL + "/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": INTRA_UID,
        "client_secret": INTRA_SECRET_KEY,
    }
    try:
        response = requests.post(URI, data=data)
        response_data = response.json()
        if response.status_code != 200:
            return JsonResponse(response_data, status=response.status_code)
        
        token = response_data.get("access_token")
        expires_in = response_data.get("expires_in")
        if not token or not expires_in:
            error_message = {"error": "No access_token or expires_in in response"}
            return JsonResponse(error_message, status=400)
        cache.set(token, True, timeout=expires_in)
        # TODO: add jwt_secret to .env file
        JWT_SECRET = getenv("JWT_SECRET")
        encoded_jwt = jwt.encode({"access_token": token}, JWT_SECRET, algorithm="HS256")
        return JsonResponse({"jwt": encoded_jwt}, status=200)

    except requests.RequestException as e:
        error_message = {"error": str(e)}
        return JsonResponse(error_message, status=500)

def exchange_access_token(request):
    """
    code를 access_token으로 교환
    access_token을 cache에 저장해서 
    expires_in을 체크하는 방식
    """
    INTRA_UID = getenv("INTRA_UID")
    INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
    URI = API_URL + "/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": INTRA_UID,
        "client_secret": INTRA_SECRET_KEY,
        # TODO: code 값을 받아올 것
        "code": "",
        "redirect_uri": getenv("REDIRECT_URI"),
        "state": getenv("STATE"),
    }
    try:
        response = requests.post(URI, data=data)
        response_data = response.json()
        if response.status_code != 200:
            return JsonResponse(response_data, status=response.status_code)
        
        token = response_data.get("access_token")
        expires_in = response_data.get("expires_in")
        if not token:
            error_message = {"error": "No access token in response"}
            return JsonResponse(error_message, status=400)
        cache.set(token, True, timeout=expires_in)
        # TODO: add jwt_secret to .env file
        JWT_SECRET = getenv("JWT_SECRET")
        encoded_jwt = jwt.encode({"access_token": token}, JWT_SECRET, algorithm="HS256")
        return JsonResponse({"jwt": encoded_jwt}, status=200)

    except requests.RequestException as e:
        error_message = {"error": str(e)}
        return JsonResponse(error_message, status=500)

def redirect(request):
    """
    42intra로 redirect해서 로그인 할 경우 정보를 반환
    frontend에서 받은 정보를 backend에 전달해야 하는 로직
    """
    params = {
        "client_id": getenv("INTRA_UID"),
        "redirect_uri": getenv("REDIRECT_URI"),
        "response_type": "code",
        "scope": "public",
        "state": getenv("STATE"),
    }
    base_url = "https://api.intra.42.fr/oauth/authorize"
    encoded_params = urlencode(params)
    url = f"{base_url}?{encoded_params}"
    return HttpResponseRedirect(url)