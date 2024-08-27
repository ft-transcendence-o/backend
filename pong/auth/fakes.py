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
                "otp_verified": True
            }
            return await f(self, request, fake_decoded_jwt, *args, **kwargs)
        return decorated_function
    return decorator

mock_login_required = mock_decorator(check_otp=True)
mock_token_required = mock_decorator(check_otp=False)

def fake_decorators():
    return patch.multiple(
        'auth.decorators',
        login_required=mock_login_required,
        token_required=mock_token_required
    )

FAKE_USER = {
        "id": 1,
        "email": "test@example.com",
        "login": "testuser",
        "usual_full_name": "Test User",
        "image_link": "http://example.com/image.jpg",
    }

FAKE_DECODED_JWT = {
    "custom_exp": 1234567890,
    "access_token": "access_token",
    "user_id": 1,
    "otp_verified": True
}

FAKE_JWT = jwt.encode(FAKE_DECODED_JWT, JWT_SECRET, algorithm="HS256")