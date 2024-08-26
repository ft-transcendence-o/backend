from asgiref.sync import sync_to_async
from django.http import JsonResponse, HttpResponseRedirect
from functools import wraps
from os import getenv
import aiohttp
import jwt

from authentication.models import User
from authentication.utils import get_user_data


def auth_decorator_factory(check_otp=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            """
            클라이언트 인증 확인 데코레이터
            token만 확인하는 단계와 OTP를 확인하는 2가지 단계로 나뉨
            token의 유효기간이 만료되었을 경우 refresh

            :param check_otp: OTP 통과 확인이 필요한지 나타내는 인자
            :cookie jwt: access_token을 담은 JWT
            """
            encoded_jwt = request.COOKIES.get("jwt")
            if not encoded_jwt:
                return JsonResponse({"error": "No jwt in request"}, status=401)

            try:
                decoded_jwt = jwt.decode(encoded_jwt, JWT_SECRET, algorithms=["HS256"])
            except:
                return JsonResponse({"error": "Decoding jwt failed"}, status=401)

            expected_keys = ("custom_exp", "access_token", "user_id", "otp_verified")
            if not all(key in decoded_jwt for key in expected_keys):
                return JsonResponse({"error": "Invalid jwt error"}, status=401)

            custom_exp = decoded_jwt.get("custom_exp")
            expiration_time = datetime.fromisoformat(custom_exp.rstrip("Z"))
            # 토큰이 만료되지 않은 경우
            if expiration_time > datetime.now():
                return await func(self, request, decoded_jwt, *args, **kwargs)

            # 토큰이 만료된 경우
            try:
                update_jwt_data = await refresh_access_token(request, decoded_jwt)
            except:
                return JsonResponse({"error": "Failed refresh access token"})

            user_data = await get_user_data(user_id)
            # 권한에 문제가 없을 경우 response는 None
            response = check_user_authorization(check_otp, update_jwt_data, user_data)
            if not response:
                response = await func(self, request, decoded_jwt, *args, **kwargs)
            response.set_cookie("jwt", encoded_jwt, httponly=True, secure=True, samesite="Lax")
            return response

        return wrapper

    return decorator

def check_user_authorization(check_otp, decoded_jwt, user_data):
    otp_verified = decoded_jwt.get("otp_verified")
    if check_otp and otp_verified == False:
        return JsonResponse(
            {
                "error": "Need OTP authentication",
                "otp_verified": otp_verified,
                "show_otp_qr": user_data.get("is_verified"),
            },
            status=403,
        )

    if check_otp == False and otp_verified:
        return JsonResponse({"error": "Already passed OTP authentication"}, status=403)
    return None

async def refresh_access_token(request, decoded_jwt):
    user_id = decoded_jwt.get("user_id")
    tokens = await fetch_new_tokens(user_id)
    await set_refresh_token_in_db(user_id, tokens["refresh_token"])
    update_jwt_data = {
        "custom_exp": timezone.now() + timedelta(seconds=JWT_EXPIRED),
        "access_token": tokens["access_token"],
        "user_id": decoded_jwt.get("user_id"),
        "otp_verified": decoded_jwt.get("otp_verified"),
    },
    return update_jwt_data

async def fetch_new_tokens(user_id):
    refresh_token = await get_refresh_token_from_db(user_id)
    data = {
        "grant_type": "refresh_token",
        "client_id": INTRA_UID,
        "client_secret": INTRA_SECRET_KEY,
        "redirect_uri": REDIRECT_URI,
        "refresh_token": refresh_token,
        "state": STATE,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/oauth/token", data=data) as response:
                response_data = await response.json()
                if response.status != 200:
                    raise Exception("42auth fetch failed")
                return {
                    "access_token": response_data.get("access_token"),
                    "refresh_token": response_data.get("refresh_token"),
                }
    except aiohttp.ClientError:
        raise Exception("aiohttp error")


@sync_to_async
def get_refresh_token_from_db(user_id):
    user = User.objects.only("refresh_token").get(id=user_id)
    return user.refresh_token

@sync_to_async
def set_refresh_token_in_db(user_id, refresh_token):
    return User.objects.filter(id=user_id).update(refresh_token=refresh_token)

login_required = auth_decorator_factory(check_otp=True)
token_required = auth_decorator_factory(check_otp=False)
