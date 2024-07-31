from django.test import TestCase, AsyncClient, RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from authentication.auth import OTPView, MAX_ATTEMPTS, LOCK_ACCOUNT
from unittest.mock import patch, MagicMock
import json



class UserInfoTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse('user_info')
        self.valid_token = 'valid_token'
        self.invalid_token = 'invalid_token'
        self.user_data = {
            'id': 1,
            'email': 'test@example.com',
            'login': 'testuser',
            'usual_full_name': 'Test User',
            'image_link': 'http://example.com/image.jpg'
        }

    async def test_get_user_info_success(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = self.user_data

            response = await self.client.get(
                self.url,
                Authorization=f'Bearer {self.valid_token}'
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), self.user_data)

    async def test_get_user_info_fail(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = None

            response = await self.client.get(
                self.url,
                Authorization = f'Bearer {self.valid_token}'
            )

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "Invalid token"})

    async def test_get_invalid_token(self):
        with patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = None

            response = await self.client.get(self.url)

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "No jwt in request"})


    async def test_get_no_token(self):
        with patch('authentication.auth.token_required') as mock_token_required:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "No jwt in request"}
            mock_token_required.side_effect = lambda func: lambda request, *args, **kwargs: mock_response

            response = await self.client.get(self.url)

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "No jwt in request"})



class QRcodeViewTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse('otp_qrcode')
        self.valid_token = 'valid_token'
        self.invalid_token = 'invalid_token'
        self.user_data = {
            'id': 1,
            'email': 'test@example.com',
            'login': 'testuser',
            'usual_full_name': 'Test User',
            'image_link': 'http://example.com/image.jpg',
            'secret': 'JBSWY3DPEHPK3PXP'
        }

    async def test_get_qrcode_success(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = self.user_data

            response = await self.client.get(
                self.url,
                headers={'Authorization': f'Bearer {self.valid_token}'}
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn('otpauth_uri', response.json())

    async def test_get_user_info_no_user_data(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.side_effect = [self.user_data, None]

            response = await self.client.get(
                self.url,
                headers={'Authorization': f'Bearer {self.valid_token}'}
            )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"error": "User data not found"})

    async def test_get_user_info_no_secret(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            user_data_no_secret = self.user_data.copy()
            user_data_no_secret.pop('secret')
            mock_cache_aget.side_effect = [self.user_data, user_data_no_secret]

            response = await self.client.get(
                self.url,
                headers={'Authorization': f'Bearer {self.valid_token}'}
            )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"error": "User secret not found"})


class OTPViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = OTPView()
        self.url = reverse('otp_verify')

        self.user_id = 1
        self.access_token = "test_token"
        self.otp_secret = "ABCDEFGHIJKLMNOP"
        self.user_data = {
            'id': 1,
            'email': 'test@example.com',
            'login': 'testuser',
            'usual_full_name': 'Test User',
            'image_link': 'http://example.com/image.jpg'
        }

        self.mock_cache_aget = patch('authentication.auth.cache.aget').start()
        self.mock_get_otp_data = patch('authentication.auth.OTPView.get_otp_data').start()
        self.mock_verify_otp = patch('authentication.auth.OTPView.verify_otp').start()
        self.mock_update_otp_success = patch('authentication.auth.OTPView.update_otp_success').start()
        self.mock_update_otp_data = patch('authentication.auth.OTPView.update_otp_data').start()
        
        self.mock_validate_jwt = patch('authentication.decorators.validate_jwt').start()
        self.mock_token_required = patch('authentication.auth.token_required').start()

    def tearDown(self):
        patch.stopall()

    async def test_success(self):
        self.mock_validate_jwt.return_value = {'access_token': self.access_token}, False
        self.mock_token_required.return_value = lambda f: f
        self.mock_cache_aget.return_value = self.user_data
        self.mock_get_otp_data.return_value = {
            'secret': self.otp_secret,
            'attempts': 0,
            'last_attempt': timezone.now(),
            'is_locked': False,
            'is_verified': False
        }
        self.mock_verify_otp.return_value = True

        request = self.factory.post(self.url, data=json.dumps({'input_password': '123456'}),
                                    content_type='application/json')

        response = await self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"success": "OTP authentication verified"})
        self.mock_update_otp_success.assert_called_once()

    async def test_incorrect_otp(self):
        self.mock_validate_jwt.return_value = {'access_token': self.access_token}, False
        self.mock_token_required.return_value = lambda f: f
        self.mock_cache_aget.return_value = self.user_data
        self.mock_get_otp_data.return_value = {
            'secret': self.otp_secret,
            'attempts': 0,
            'last_attempt': timezone.now(),
            'is_locked': False,
            'is_verified': False
        }
        self.mock_verify_otp.return_value = False

        request = self.factory.post(self.url, data=json.dumps({'input_password': '123456'}),
                                    content_type='application/json')

        response = await self.view.post(request)

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["error"], "Incorrect password.")
        self.assertEqual(response_data["remain_attempts"], MAX_ATTEMPTS - 1)
        self.mock_update_otp_data.assert_called_once()

    async def test_account_locked(self):
        self.mock_validate_jwt.return_value = {'access_token': self.access_token}, False
        self.mock_token_required.return_value = lambda f: f
        self.mock_cache_aget.return_value = self.user_data
        self.mock_get_otp_data.return_value = {
            'secret': self.otp_secret,
            'attempts': MAX_ATTEMPTS,
            'last_attempt': timezone.now(),
            'is_locked': True,
            'is_verified': False
        }

        request = self.factory.post(self.url, data=json.dumps({'input_password': '123456'}),
                                    content_type='application/json')

        response = await self.view.post(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {"error": "Account is locked. try later"})

    async def test_account_unlock(self):
        self.mock_validate_jwt.return_value = {'access_token': self.access_token}, False
        self.mock_token_required.return_value = lambda f: f
        self.mock_cache_aget.return_value = self.user_data
        self.mock_get_otp_data.return_value = {
            'secret': self.otp_secret,
            'attempts': MAX_ATTEMPTS,
            'last_attempt': timezone.now() - timedelta(minutes=LOCK_ACCOUNT),
            'is_locked': True,
            'is_verified': False
        }
        self.mock_verify_otp.return_value = True

        request = self.factory.post(self.url, data=json.dumps({'input_password': '123456'}),
                                    content_type='application/json')

        response = await self.view.post(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'success': 'OTP authentication verified'})

    async def test_otp_data_not_found(self):
        self.mock_validate_jwt.return_value = {'access_token': self.access_token}, False
        self.mock_token_required.return_value = lambda f: f
        self.mock_cache_aget.return_value = self.user_data
        self.mock_get_otp_data.return_value = None

        request = self.factory.post(self.url, data=json.dumps({'input_password': '123456'}),
                                    content_type='application/json')

        response = await self.view.post(request)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.content), {"error": "Can't found OTP data."})

    async def test_otp_attempts_count(self):
        self.mock_validate_jwt.return_value = {'access_token': self.access_token}, False
        self.mock_token_required.return_value = lambda f: f
        self.mock_cache_aget.return_value = self.user_data
        self.mock_get_otp_data.return_value = {
            'secret': self.otp_secret,
            'attempts': 0,
            'last_attempt': timezone.now(),
            'is_locked': False,
            'is_verified': False
        }
        self.mock_verify_otp.return_value = False

        for i in range(MAX_ATTEMPTS):
            request = self.factory.post(self.url, data=json.dumps({'input_password': '123456'}),
                                        content_type='application/json')
            response = await self.view.post(request)
            if i < MAX_ATTEMPTS - 1:
                self.assertEqual(response.status_code, 400)
                self.assertEqual(json.loads(response.content)["remain_attempts"], MAX_ATTEMPTS - (i + 1))
            else:
                self.assertEqual(response.status_code, 403)
                self.assertEqual(json.loads(response.content)["error"], "Maximum number of attempts exceeded. Please try again after 15 minutes.")