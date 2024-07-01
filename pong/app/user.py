from django.http import HttpResponse
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

def take_access_token(request):
    """
    access token을 발급받는 곳
    """
    INTRA_UID = getenv("INTRA_UID")
    INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
    URL = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": INTRA_UID,
        "client_secret": INTRA_SECRET_KEY,
    }
    response = requests.post(URL, data=data)
    return HttpResponse(response.text)

def redirect(request):
    """
    42intra로 redirect해서 로그인 할 경우 정보를 반환
    frontend에서 받은 정보를 backend에 전달해야 하는 경우
    """
    URL = getenv("REDIRECT_URI")
    r = requests.get(URL)
    return HttpResponse(r.text)