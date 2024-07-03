from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from os import getenv
import requests

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
"""

API_URL = getenv("API_URL")

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
    """
    URI = API_URL + "/auth/token/info"
    token = "81a462114352aa75674c78cf816567ad802858724b3494f524f274532ab2cc24"
    headers = { "Authorization": "Bearer %s" % token }
    response = requests.get(URI, headers=headers)
    return HttpResponse(response.text)


def temp_access_token(request):
    """
    테스트용 grant_type == client_credentials
    """
    INTRA_UID = getenv("INTRA_UID")
    INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
    URI = API_URL + "oauth/token"
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
        return JsonResponse(response_data, status=200)

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
        # code 값을 받아올 것
        " code": "",
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
        return JsonResponse(response_data, status=200)

    except requests.RequestException as e:
        error_message = {"error": str(e)}
        return JsonResponse(error_message, status=500)

def redirect(request):
    """
    42intra로 redirect해서 로그인 할 경우 정보를 반환
    frontend에서 받은 정보를 backend에 전달해야 하는 경우
    """
    URI = getenv("REDIRECT_URI")
    r = requests.get(URI)
    return HttpResponse(r.text)