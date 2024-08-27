from django.test import TestCase, AsyncClient, RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import json
import jwt
from functools import wraps

from .models import OTPSecret, User
from .constants import MAX_ATTEMPTS
from .fakes import fake_decorators, FAKE_USER, FAKE_JWT

fake_decoded_jwt = {
    "user_id": 1,
    "access_token": "access_token",
    "custom_exp": 1234567890,
    "otp_verified": True
}

def mock_decorator(check_otp):
    def decorator(f):
        @wraps(f)
        async def decorated_function(self, request, *args, **kwargs):
            return await f(self, request, fake_decoded_jwt, *args, **kwargs)
        return decorated_function
    return decorator

mock_login_required = mock_decorator(check_otp=True)
mock_token_required = mock_decorator(check_otp=False)

with patch('auth.decorators.login_required', mock_login_required):
    with patch('auth.decorators.token_required', mock_token_required):
        from .views import (
            OAuthView,
            OTPView,
            UserInfo
        )

class UserInfoTestCase(TestCase):
    """Integration tests for UserInfo View class"""

    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse("user_info")
        self.user_data = {
            "id": 1,
            "email": "test@example.com",
            "login": "testuser",
            "usual_full_name": "Test User",
            "image_link": "http://example.com/image.jpg",
        }

    @patch('auth.views.get_user_data')
    async def test_get_invalid_token(self, mock_get_user_data):
        mock_get_user_data.return_value = None

        response = await self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Invalid token")

    @patch('auth.views.get_user_data')
    async def test_get_success(self, mock_get_user_data):
        mock_get_user_data.return_value = self.user_data

        response = await self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user_data["email"])
        self.assertEqual(response.json()["login"], self.user_data["login"])

    # async def test_get_user_info_success(self):
    #     """Test UserInfo View

    #     정상적으로 유저 정보를 반환하는 경우
    #     """
        
    #     with patch("auth.views.login_required") as mock_login_required:

    #         mock_validate_jwt.return_value = {"access_token": self.valid_token}, False
    #         mock_token_required.return_value = lambda f: f
    #         mock_cache_aget.return_value = self.user_data

    #         response = await self.client.get(self.url, Authorization=f"Bearer {self.valid_token}")

    #         self.assertEqual(response.status_code, 200)
    #         self.assertEqual(response.json(), self.user_data)

    # async def test_get_user_info_fail(self):
    #     """Test UserInfo View

    #     캐싱에 실패하여 유저 정보를 가져오지 못함
    #     """
    #     with patch("auth.decorators.validate_jwt") as mock_validate_jwt, patch(
    #         "auth.auth.cache.aget"
    #     ) as mock_cache_aget, patch("auth.auth.token_required") as mock_token_required:

    #         mock_validate_jwt.return_value = {"access_token": self.valid_token}, False
    #         mock_token_required.return_value = lambda f: f
    #         mock_cache_aget.return_value = None

    #         response = await self.client.get(self.url, Authorization=f"Bearer {self.valid_token}")

    #         self.assertEqual(response.status_code, 401)
    #         self.assertEqual(response.json(), {"error": "Invalid token"})

    # async def test_get_invalid_token(self):
    #     """Test UserInfo View

    #     헤더에 JWT가 포함되어 있지 않음
    #     """
    #     with patch("auth.auth.cache.aget") as mock_cache_aget, patch(
    #         "auth.auth.token_required"
    #     ) as mock_token_required:

    #         mock_token_required.return_value = lambda f: f
    #         mock_cache_aget.return_value = None

    #         response = await self.client.get(self.url)

    #         self.assertEqual(response.status_code, 401)
    #         self.assertEqual(response.json(), {"error": "No jwt in request"})

    # async def test_get_no_token(self):
    #     """Test UserInfo View

    #     캐싱에 실패하여 유저 정보를 가져오지 못한 경우
    #     """
    #     with patch("auth.auth.token_required") as mock_token_required:
    #         mock_response = MagicMock()
    #         mock_response.status_code = 401
    #         mock_response.json.return_value = {"error": "No jwt in request"}
    #         mock_token_required.return_value = lambda f: f

    #         response = await self.client.get(self.url)

    #         self.assertEqual(response.status_code, 401)
    #         self.assertEqual(response.json(), {"error": "No jwt in request"})


# class QRcodeViewTestCase(TestCase):
#     """Integration tests for QRcode View class"""

#     def setUp(self):
#         self.client = AsyncClient()
#         self.url = reverse("otp_qrcode")
#         self.valid_token = "valid_token"
#         self.invalid_token = "invalid_token"
#         self.user_data = {
#             "id": 1,
#             "email": "test@example.com",
#             "login": "testuser",
#             "usual_full_name": "Test User",
#             "image_link": "http://example.com/image.jpg",
#             "secret": "JBSWY3DPEHPK3PXP",
#         }

#     async def test_get_qrcode_success(self):
#         """Test QRcode View

#         성공적으로  QRcode를 받아옴
#         """
#         with patch("auth.decorators.validate_jwt") as mock_validate_jwt, patch(
#             "auth.auth.cache.aget"
#         ) as mock_cache_aget, patch("auth.auth.token_required") as mock_token_required:

#             mock_validate_jwt.return_value = {"access_token": self.valid_token}, False
#             mock_token_required.return_value = lambda f: f
#             mock_cache_aget.return_value = self.user_data

#             response = await self.client.get(
#                 self.url, headers={"Authorization": f"Bearer {self.valid_token}"}
#             )

#             self.assertEqual(response.status_code, 200)
#             self.assertIn("otpauth_uri", response.json())

#     async def test_get_user_info_no_user_data(self):
#         """Test QRcode View

#         user_data를 찾지 못해서 실패한 경우
#         """
#         with patch("auth.decorators.validate_jwt") as mock_validate_jwt, patch(
#             "auth.auth.cache.aget"
#         ) as mock_cache_aget, patch("auth.auth.token_required") as mock_token_required:

#             mock_validate_jwt.return_value = {"access_token": self.valid_token}, False
#             mock_token_required.return_value = lambda f: f
#             mock_cache_aget.side_effect = [self.user_data, None]

#             response = await self.client.get(
#                 self.url, headers={"Authorization": f"Bearer {self.valid_token}"}
#             )

#             self.assertEqual(response.status_code, 400)
#             self.assertEqual(response.json(), {"error": "User data not found"})

#     async def test_get_user_info_no_secret(self):
#         """Test QRcode View

#         DB에 secret값이 설정되지 않거나 캐시로 불러오지 못함
#         """
#         with patch("auth.decorators.validate_jwt") as mock_validate_jwt, patch(
#             "auth.auth.cache.aget"
#         ) as mock_cache_aget, patch("auth.auth.token_required") as mock_token_required:

#             mock_validate_jwt.return_value = {"access_token": self.valid_token}, False
#             mock_token_required.return_value = lambda f: f
#             user_data_no_secret = self.user_data.copy()
#             user_data_no_secret.pop("secret")
#             mock_cache_aget.side_effect = [self.user_data, user_data_no_secret]

#             response = await self.client.get(
#                 self.url, headers={"Authorization": f"Bearer {self.valid_token}"}
#             )

#             self.assertEqual(response.status_code, 400)
#             self.assertEqual(response.json(), {"error": "User secret not found"})


# class OTPViewTest(TestCase):
#     """Integration tests for OTP View class"""

#     def setUp(self):
#         self.factory = RequestFactory()
#         self.view = OTPView()
#         self.url = reverse("otp_verify")

#         self.user_id = 1
#         self.access_token = "test_token"
#         self.otp_secret = "ABCDEFGHIJKLMNOP"
#         self.user_data = {
#             "id": 1,
#             "email": "test@example.com",
#             "login": "testuser",
#             "usual_full_name": "Test User",
#             "image_link": "http://example.com/image.jpg",
#         }

#         self.mock_cache_aget = patch("auth.auth.cache.aget").start()
#         self.mock_get_otp_data = patch("auth.auth.OTPView.get_otp_data").start()
#         self.mock_verify_otp = patch("auth.auth.OTPView.verify_otp").start()
#         self.mock_update_otp_success = patch(
#             "auth.auth.OTPView.update_otp_success"
#         ).start()
#         self.mock_update_otp_data = patch("auth.auth.OTPView.update_otp_data").start()

#         self.mock_validate_jwt = patch("auth.decorators.validate_jwt").start()
#         self.mock_token_required = patch("auth.auth.token_required").start()

#     def tearDown(self):
#         patch.stopall()

#     async def test_success(self):
#         """Test OTP View

#         OTP패스워가 일치함
#         """
#         self.mock_validate_jwt.return_value = {"access_token": self.access_token}, False
#         self.mock_token_required.return_value = lambda f: f
#         self.mock_cache_aget.return_value = self.user_data
#         self.mock_get_otp_data.return_value = {
#             "secret": self.otp_secret,
#             "attempts": 0,
#             "last_attempt": timezone.now(),
#             "is_locked": False,
#             "is_verified": False,
#         }
#         self.mock_verify_otp.return_value = True

#         request = self.factory.post(
#             self.url, data=json.dumps({"input_password": "123456"}), content_type="application/json"
#         )

#         response = await self.view.post(request)

#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(json.loads(response.content), {"success": "OTP authentication verified"})
#         self.mock_update_otp_success.assert_called_once()

#     async def test_incorrect_otp(self):
#         """Test OTP View

#         OTP패스워가 일치하지 않음
#         """
#         self.mock_validate_jwt.return_value = {"access_token": self.access_token}, False
#         self.mock_token_required.return_value = lambda f: f
#         self.mock_cache_aget.return_value = self.user_data
#         self.mock_get_otp_data.return_value = {
#             "secret": self.otp_secret,
#             "attempts": 0,
#             "last_attempt": timezone.now(),
#             "is_locked": False,
#             "is_verified": False,
#         }
#         self.mock_verify_otp.return_value = False

#         request = self.factory.post(
#             self.url, data=json.dumps({"input_password": "123456"}), content_type="application/json"
#         )

#         response = await self.view.post(request)

#         self.assertEqual(response.status_code, 400)
#         response_data = json.loads(response.content)
#         self.assertEqual(response_data["error"], "Incorrect password.")
#         self.assertEqual(response_data["remain_attempts"], MAX_ATTEMPTS - 1)
#         self.mock_update_otp_data.assert_called_once()

#     async def test_account_locked(self):
#         """Test OTP View

#         계정이 잠금되어 실패한 경우
#         """
#         self.mock_validate_jwt.return_value = {"access_token": self.access_token}, False
#         self.mock_token_required.return_value = lambda f: f
#         self.mock_cache_aget.return_value = self.user_data
#         self.mock_get_otp_data.return_value = {
#             "secret": self.otp_secret,
#             "attempts": MAX_ATTEMPTS,
#             "last_attempt": timezone.now(),
#             "is_locked": True,
#             "is_verified": False,
#         }

#         request = self.factory.post(
#             self.url, data=json.dumps({"input_password": "123456"}), content_type="application/json"
#         )

#         response = await self.view.post(request)

#         self.assertEqual(response.status_code, 403)
#         self.assertEqual(json.loads(response.content), {"error": "Account is locked. try later"})

#     async def test_account_unlock(self):
#         """Test OTP View

#         계정 잠금 시간이 경과한 후 시도했을 경우
#         """
#         self.mock_validate_jwt.return_value = {"access_token": self.access_token}, False
#         self.mock_token_required.return_value = lambda f: f
#         self.mock_cache_aget.return_value = self.user_data
#         self.mock_get_otp_data.return_value = {
#             "secret": self.otp_secret,
#             "attempts": MAX_ATTEMPTS,
#             "last_attempt": timezone.now() - timedelta(minutes=LOCK_ACCOUNT),
#             "is_locked": True,
#             "is_verified": False,
#         }
#         self.mock_verify_otp.return_value = True

#         request = self.factory.post(
#             self.url, data=json.dumps({"input_password": "123456"}), content_type="application/json"
#         )

#         response = await self.view.post(request)

#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(json.loads(response.content), {"success": "OTP authentication verified"})

#     async def test_otp_data_not_found(self):
#         """Test OTP View

#         계정이 잠금되어 실패한 경우
#         """
#         self.mock_validate_jwt.return_value = {"access_token": self.access_token}, False
#         self.mock_token_required.return_value = lambda f: f
#         self.mock_cache_aget.return_value = self.user_data
#         self.mock_get_otp_data.return_value = None

#         request = self.factory.post(
#             self.url, data=json.dumps({"input_password": "123456"}), content_type="application/json"
#         )

#         response = await self.view.post(request)

#         self.assertEqual(response.status_code, 500)
#         self.assertEqual(json.loads(response.content), {"error": "Can't found OTP data."})

#     async def test_otp_attempts_count(self):
#         """Test OTP View

#         비밀번호 시도 횟수 체크 및 계정 잠금
#         """
#         self.mock_validate_jwt.return_value = {"access_token": self.access_token}, False
#         self.mock_token_required.return_value = lambda f: f
#         self.mock_cache_aget.return_value = self.user_data
#         self.mock_get_otp_data.return_value = {
#             "secret": self.otp_secret,
#             "attempts": 0,
#             "last_attempt": timezone.now(),
#             "is_locked": False,
#             "is_verified": False,
#         }
#         self.mock_verify_otp.return_value = False

#         for i in range(MAX_ATTEMPTS):
#             request = self.factory.post(
#                 self.url,
#                 data=json.dumps({"input_password": "123456"}),
#                 content_type="application/json",
#             )
#             response = await self.view.post(request)
#             if i < MAX_ATTEMPTS - 1:
#                 self.assertEqual(response.status_code, 400)
#                 self.assertEqual(
#                     json.loads(response.content)["remain_attempts"], MAX_ATTEMPTS - (i + 1)
#                 )
#             else:
#                 self.assertEqual(response.status_code, 403)
#                 self.assertEqual(
#                     json.loads(response.content)["error"],
#                     "Maximum number of attempts exceeded. Please try again after 15 minutes.",
#                 )


# class OAuthViewTest(TestCase):
#     """Integration tests for OAuth View class"""

#     def setUp(self):
#         self.factory = RequestFactory()
#         self.view = OAuthView()
#         self.url = reverse("token")

#         self.user_id = 1
#         self.access_token = "access_token"
#         self.encoded_jwt = jwt.encode(
#             {"access_token": self.access_token}, JWT_SECRET, algorithm="HS256"
#         )
#         self.otp_secret = "ABCDEFGHIJKLMNOP"
#         self.user_data = {
#             "id": 1,
#             "email": "test@example.com",
#             "login": "testuser",
#             "usual_full_name": "Test User",
#             "image_link": "http://example.com/image.jpg",
#         }
#         self.user_obj = User(*self.user_data)
#         self.otp_obj = OTPSecret(user_id=1, secret="Fake", attempts=0, is_verified=False)

#         self.mock_exchange_code_for_token = patch(
#             "auth.auth.OAuthView.exchange_code_for_token"
#         ).start()
#         self.mock_get_user_info = patch("auth.auth.OAuthView.get_user_info").start()

#     def tearDown(self):
#         patch.stopall()

#     async def test_get_success(self):
#         """Test OAuth View

#         get method, 성공 시 리다이렉션 URI 및 response cookie 확인
#         """
#         self.mock_exchange_code_for_token.return_value = self.access_token
#         self.mock_get_user_info.return_value = (True, {"user": "data"})

#         request = self.factory.get(self.url)
#         response = await self.view.get(request)

#         self.assertEqual(response.status_code, 302)
#         self.assertEqual(response.url, "http://127.0.0.1:5500/main")
#         self.assertIn("jwt", response.cookies)

#     async def test_get_failure_no_access_token(self):
#         """Test OAuth View

#         get method, access_token이 없어서 실패한 경우
#         """
#         self.mock_exchange_code_for_token.return_value = None

#         request = self.factory.get(self.url)
#         response = await self.view.get(request)

#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(json.loads(response.content)["error"], "Failed to obtain access token")

#     @patch("auth.auth.cache.aget")
#     @patch("auth.decorators.validate_jwt")
#     @patch("auth.auth.token_required")
#     async def test_delete(self, mock_token_required, mock_validate_jwt, mock_user_data):
#         """Test OAuth View

#         delete method 성공
#         """
#         mock_user_data.return_value = self.user_data
#         mock_validate_jwt.return_value = self.access_token, False
#         mock_token_required.return_value = lambda f: f

#         request = self.factory.delete(self.url, self.access_token)
#         response = await self.view.delete(request)

#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(json.loads(response.content)["message"], "logout success")

#     async def test_post_success(self):
#         """Test OAuth View

#         post method의 경우 code를 받아서 token으로 교환하는 과정 확인
#         반환하는 json값들 확인
#         """
#         self.mock_exchange_code_for_token.return_value = self.access_token
#         self.mock_get_user_info.return_value = (True, {"user": self.user_obj, "otp": self.otp_obj})

#         request = self.factory.post(
#             self.url, data='{"code":"fake_code"}', content_type="application/json"
#         )
#         response = await self.view.post(request)

#         self.assertEqual(response.status_code, 200)
#         self.assertIn(json.loads(response.content)["jwt"], self.encoded_jwt)
#         self.assertEqual(json.loads(response.content)["otp_verified"], False)
#         self.assertEqual(json.loads(response.content)["show_otp_qr"], False)
