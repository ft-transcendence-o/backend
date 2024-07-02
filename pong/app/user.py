from django.http import HttpResponse, JsonResponse
from os import getenv
import requests

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

def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        """
        access_token의 유효성을 검사하는 데코레이터
        :param request의 헤더에 Authorization이라는 name을 가진 value값을 사용
        """
        access_token = request.headers.get('Authorization')
        if not access_token:
            return JsonResponse({'error': 'No access token provided'}, status=401)

        if access_token.startswith('Bearer '):
            access_token = access_token[7:]

        if not is_valid_token(access_token):
            return JsonResponse({'error': 'Invalid access token'}, status=401)

        return func(request, *args, **kwargs)
    return wrapper

def is_valid_token(token):
    """
    access_token을 발급 받고 테스트
    expired 및 status_code를 사용해 유효한지 확인
    """
    URL = "https://api.intra.42.fr/oauth/token/info"
    headers = { "Authorization": "Bearer %s" % token }
    response = requests.get(URL, headers=headers)
    return HttpResponse(response.text)

def exchange_access_token(request):
    """
    code를 access_token으로 교환
    """
    INTRA_UID = getenv("INTRA_UID")
    INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
    URL = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": INTRA_UID,
        "client_secret": INTRA_SECRET_KEY,
        # code 값을 받아올 것
        " code": "",
    }
    try:
        response = requests.post(URL, data=data)
        response_data = response.json()
        if response.status_code != 200:
            return JsonResponse(response_data, status=response.status_code)
        
        token = response_data.get("access_token")
        if not token:
            error_message = {"error": "No access token in response"}
            return JsonResponse(error_message, status=400)
        return JsonResponse(response_data, status=200)

    except requests.RequestException as e:
        error_message = {"error": str(e)}
        return JsonResponse(error_message, status=500)

def redirect(request):
    """
    42intra로 redirect해서 로그인 할 경우 정보를 반환
    frontend에서 받은 정보를 backend에 전달해야 하는 경우
    """
    URL = getenv("REDIRECT_URI")
    r = requests.get(URL)
    return HttpResponse(r.text)