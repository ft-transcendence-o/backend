from unittest.mock import patch
from datetime import timedelta
import jwt

from .constants import JWT_SECRET


def mock_decorator(check_otp=False):
    def decorator(f):
        async def decorated_function(self, request, *args, **kwargs):
            fake_decoded_jwt = {
                "user_id": 1,
                "access_token": "access_token",
                "custom_exp": 1234567890,
                "otp_verified": True,
            }
            return await f(self, request, fake_decoded_jwt, *args, **kwargs)

        return decorated_function

    return decorator


mock_login_required = mock_decorator(check_otp=True)
mock_token_required = mock_decorator(check_otp=False)


def fake_decorators():
    return patch.multiple(
        "auth.decorators", login_required=mock_login_required, token_required=mock_token_required
    )


FAKE_NORMAL_GAME = {
    "id": 12,
    "user_id": 1,
    "player1Nick": "player1",
    "player2Nick": "player2",
    "player1Score": "3",
    "player2Score": "2",
    "mode": "normal"
}

FAKE_TOURNAMENT_GAME = {
    "user_id": 1,
    "game1": 1,
    "game2": 2,
    "game3": 3,
}

FAKE_USER_DATA = {
    "login": "testuser",
    "need_otp": True,
    "is_verified": False,
    "secret": "TESTSECRET",
    "email": "test@example.com",
}

FAKE_USER = {
    "id": 1,
    "email": "test@example.com",
    "login": "testuser",
    "usual_full_name": "Test User",
    "image_link": "http://example.com/image.jpg",
}

FAKE_DECODED_JWT_PASS_OTP = {
    "custom_exp": 1234567890,
    "access_token": "access_token",
    "user_id": 1,
    "otp_verified": True,
}

FAKE_DECODED_JWT_NO_OTP = {
    "custom_exp": 1234567890,
    "access_token": "access_token",
    "user_id": 1,
    "otp_verified": False,
}

FAKE_JWT_NO_OTP = jwt.encode(FAKE_DECODED_JWT_NO_OTP, JWT_SECRET, algorithm="HS256")
FAKE_JWT_PASS_OTP = jwt.encode(FAKE_DECODED_JWT_PASS_OTP, JWT_SECRET, algorithm="HS256")
