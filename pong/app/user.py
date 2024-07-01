from django.http import HttpResponse
from os import getenv
import requests

def test(request):
    INTRA_UID = getenv("INTRA_UID")
    INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
    URL = "https://api.intra.42.fr/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": INTRA_UID,
        "client_secret": INTRA_SECRET_KEY,
    }
    r = requests.post(URL, data=data)
    print(r.json())
    return HttpResponse(r.text)


def redirect(request):
    URL = getenv("REDIRECT_URI")
    r = requests.get(URL)
    return HttpResponse(r.text)

def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")