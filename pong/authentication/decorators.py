from django.http import JsonResponse
from django.core.cache import cache
from functools import wraps
from os import getenv
import jwt

JWT_SECRET = getenv("JWT_SECRET")

def validate_jwt(request):
    """
    JWT 검증 및 액세스 토큰 추출 함수
    """
    encoded_jwt = request.COOKIES.get("jwt")
    if not encoded_jwt:
        return None, JsonResponse({"error": "No jwt in request"}, status=401)
    if encoded_jwt.startswith("Bearer "):
        encoded_jwt = encoded_jwt[7:]

    try:
        decoded_jwt = jwt.decode(encoded_jwt, JWT_SECRET, algorithms=["HS256"])
    except:
        return None, JsonResponse({"error": "Decoding jwt failed"}, status=401)

    user_id = decoded_jwt.get("user_id")
    if not user_id:
        return None, JsonResponse({"error": "No access token provided"}, status=401)

    return user_id, None

def auth_decorator_factory(check_otp=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, request, *args, **kwargs):
            """
            클라이언트 인증 확인 데코레이터
            token만 확인하는 단계와 OTP를 확인하는 2가지 단계로 나뉨
            :param check_otp: OTP 통과 확인이 필요한지 나타내는 인자
            :header Authorization: access_token을 담은 JWT
            """
            user_id, error_response = validate_jwt(request)
            if error_response:
                return error_response

            user_data = await cache.aget(f'user_data_{user_id}')
            if not user_data:
                return JsonResponse({"error": "Invalid token"}, status=401)

            if check_otp:
                otp_verified = await cache.aget(f'otp_passed_{user_id}')
                show_otp_qr = user_data.get('is_verified')
                if not otp_verified:
                    return JsonResponse({
                        "error": "Need OTP authentication",
                        "otp_verified": otp_verified,
                        "show_otp_qr": show_otp_qr
                    }, status=403)

            return await func(self, request, user_id, *args, **kwargs)
        return wrapper
    return decorator

login_required = auth_decorator_factory(check_otp=True)
token_required = auth_decorator_factory(check_otp=False)