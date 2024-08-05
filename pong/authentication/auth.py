from asgiref.sync import sync_to_async
from django.http import JsonResponse, HttpResponseRedirect
from django.core.cache import cache
from django.utils import timezone
from django.views import View
from django.db import transaction
from os import getenv
import aiohttp
import pyotp
import jwt
import json

from authentication.decorators import token_required, login_required
from authentication.models import User, OTPSecret

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
4. email, secret 정보를 사용하여 2FA를 실행한다
5. 첫번째 로그인의 경우 OTP에 필요한 secret을 생성하고 
    URI로 QR code를 그린다
6. QR code를 사용해 google authenticator 등록
7. OTP 입력 및 검증
"""
TOKEN_EXPIRES= 7200
LOCK_ACCOUNT = 9
MAX_ATTEMPTS = 5
API_URL = getenv("API_URL")
JWT_SECRET = getenv("JWT_SECRET")
INTRA_UID = getenv("INTRA_UID")
INTRA_SECRET_KEY = getenv("INTRA_SECRET_KEY")
REDIRECT_URI = getenv("REDIRECT_URI")
STATE = getenv("STATE")
AUTH_PAGE = getenv("AUTH_PAGE")
FRONT_BASE_URL = getenv("FRONT_BASE_URL")


class UserInfo(View):
    @token_required
    async def get(self, request, access_token):
        """
        main 화면에서 보여줄 유저 정보를 반환하는 API

        :header Authorization: 인증을 위한 JWT
        """
        user_info = await cache.aget(f'user_data_{access_token}')
        if not user_info:
            return JsonResponse({"error": "Invalid token"}, status=401)
        data = {
            'id': user_info['id'],
            'email': user_info['email'],
            'login': user_info['login'],
            'usual_full_name': user_info['usual_full_name'],
            'image_link': user_info['image_link'],
        }
        return JsonResponse(data, status=200)

class OAuthView(View):
    async def get(self, request):
        """
        code값을 token으로 변환한 후
        http header에 cookie를 저장하여 반환
        frontend의 main페이지로 리다이렉션

        :query code: 42OAuth에서 받음 code값
        """
        code = request.GET.get('code')
        access_token = await self.exchange_code_for_token(code)
        if not access_token:
            return JsonResponse({"error": "Failed to obtain access token"}, status=400)

        success, user_info = await self.get_user_info(access_token)
        if not success:
            return JsonResponse({"error": user_info}, status=500)
        encoded_jwt = jwt.encode({"access_token": access_token}, JWT_SECRET, algorithm="HS256")
        redirect_url = await self.get_redirect_url(access_token, user_info['otp'].is_verified)
        response = HttpResponseRedirect(redirect_url)
        response.set_cookie(
                "jwt",
                encoded_jwt,
                httponly=True,
                secure=True,
                samesite='Lax'
            )
        return response

    @token_required
    async def delete(self, request, access_token):
        """
        cache에 저장된 유저 정보 및 OTP패스 정보 폐기
        cookie JWT 폐기 및 홈 화면으로 리다이렉션

        :header Authorization: 인증을 위한 JWT
        """
        cache.delete(f'user_data_{access_token}')
        cache.delete(f'otp_passed_{access_token}')
        response = HttpResponseRedirect(FRONT_BASE_URL)
        response.delete_cookie('jwt')
        return response

    async def post(self, request):
        """
        frontend에서 /oauth/authorize 경로로 보낸 후 redirection되어서 오는 곳
        querystring으로 code를 가져온 후 code를 access_token으로 교환
        access_token을 cache에 저장해서 expires_in을 체크한다

        :body code: access_token과 교환하기 위한 code
        """
        code = self.extract_code(request)
        if not code:
            return JsonResponse({"error": "No code value in querystring"}, status=400)

        access_token = await self.exchange_code_for_token(code)
        if not access_token:
            return JsonResponse({"error": "Failed to obtain access token"}, status=400)

        success, user_info = await self.get_user_info(access_token)
        if not success:
            return JsonResponse({"error": user_info}, status=500)
        return await self.prepare_response(access_token, user_info)

    async def get_redirect_url(self, access_token, is_verified):
        if await cache.aget(f'otp_passed_{access_token}', False) == False:
            if is_verified == False:
                return FRONT_BASE_URL + "/QRcode"
            else:
                return FRONT_BASE_URL + "/OTP"
        else:
            return FRONT_BASE_URL + "/main"

    def extract_code(self, request):
        body = json.loads(request.body.decode('utf-8'))
        return body.get("code")

    async def exchange_code_for_token(self, code):
        """42API에서 유저 정보를 받아온다"""
        data = {
            "grant_type": "authorization_code",
            "client_id": INTRA_UID,
            "client_secret": INTRA_SECRET_KEY,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "state": STATE,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{API_URL}/oauth/token', data=data) as response:
                    if response.status != 200:
                        return None
                    response_data = await response.json()
                    return response_data.get("access_token")
        except aiohttp.ClientError:
            return None

    async def get_user_info(self, access_token):
        """
        access_token을 활용하여 user의 정보를 받아온다
        정보를 받아와서 user db에 있는지 확인한 후 없을 경우 생성
        """
        headers = {"Authorization": f'Bearer {access_token}'}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_URL}/v2/me', headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self.process_user_data(data, access_token)
                    return False, await response.json()
        except aiohttp.ClientError as e:
            return False, str(e)

    @sync_to_async
    def process_user_data(self, data, access_token):
        """
        사용자 데이터 처리 및 OTP 데이터 생성
        필요한 정보는 cache에 저장
        """
        try:
            with transaction.atomic():
                user_data = self.get_or_create_user(data)
                otp_data = self.get_or_create_otp_secret(data['id'])
            self.set_cache(user_data, otp_data, access_token)
            return True, {"user": user_data, "otp": otp_data}
        except transaction.TransactionManagementError as e:
            return False, str(e)

    async def prepare_response(self, access_token, user_info):
        encoded_jwt = jwt.encode({"access_token": access_token}, JWT_SECRET, algorithm="HS256")
        otp_verified = await cache.aget(f'otp_passed_{access_token}', False)
        return JsonResponse({
            "jwt": encoded_jwt,
            "otp_verified": otp_verified,
            "show_otp_qr": user_info['otp'].is_verified
        }, status=200)

    def set_cache(self, user_data, otp_data, access_token):
        cache_value = {
            'id': user_data.id,
            'email': user_data.email,
            'login': user_data.login,
            'usual_full_name': user_data.usual_full_name,
            'image_link': user_data.image_link,
            'need_otp': user_data.need_otp,
            'secret': otp_data.secret,
            'is_verified': otp_data.is_verified
        }
        cache.set(f'user_data_{access_token}', cache_value, TOKEN_EXPIRES)

    def get_or_create_user(self, data):
        user, _ = User.objects.get_or_create(
            id=data['id'],
            defaults={
                'email': data['email'],
                'login': data['login'],
                'usual_full_name': data['usual_full_name'],
                'image_link': data['image']['link'],
            }
        )
        return user

    def get_or_create_otp_secret(self, user_id):
        otp_secret, _ = OTPSecret.objects.get_or_create(
            user_id=user_id,
            defaults={
                'secret': pyotp.random_base32(),
                'attempts': 0,
                'last_attempt': None,
                'is_locked': False,
            }
        )
        return otp_secret


class QRcodeView(View):
    @token_required
    async def get(self, request, access_token):
        """
        QRcode에 필요한 secret값을 포함한 URI를 반환하는 함수

        :header Authorization: 인증을 위한 JWT
        """
        try:
            user_data = await self.get_user_data(access_token)
            secret = self.get_user_secret(user_data)
            uri = self.generate_otp_uri(user_data, secret)
            return JsonResponse({"otpauth_uri": uri}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
 
    # It check user data twice but still need
    async def get_user_data(self, access_token):
        user_data = await cache.aget(f'user_data_{access_token}')
        if not user_data:
            raise Exception("User data not found")
        return user_data

    def get_user_secret(self, user_data):
        secret = user_data.get('secret')
        if not secret:
            raise Exception("User secret not found")
        return secret

    def generate_otp_uri(self, user_data, secret):
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_data['email'],
            issuer_name="pong_game"
        )


class OTPView(View):
    @token_required
    async def post(self, request, access_token):
        """
        OTP 패스워드를 확인하는 view
        OTP 정보 확인 및 900초 지났을 경우 시도 횟수 초기화
        계정 잠금, 정보 없음, OTP인증 실패 확인

        cache를 사용하여 저장할 경우 퍼포먼스의 이득을 볼 수 있지만
        데이터의 정합성을 위해서 db를 확인한다

        :header Authorization: 인증을 위한 JWT
        :body input_password: 사용자가 입력한 OTP
        """
        user_data = await cache.aget(f"user_data_{access_token}")
        user_id = user_data.get('id')
        otp_data = await self.get_otp_data(user_id)
        if not otp_data:
            return JsonResponse({"error": "Can't found OTP data."}, status=500)

        now = timezone.now()
        if self.is_account_locked(otp_data, now):
            return JsonResponse({"error": "Account is locked. try later"}, status=403)

        otp_data['attempts'] += 1
        otp_data['last_attempt'] = now
        if otp_data['attempts'] >= MAX_ATTEMPTS:
            otp_data['is_locked'] = True
            await self.update_otp_data(user_id, otp_data)
            return JsonResponse({"error": "Maximum number of attempts exceeded. Please try again after 15 minutes."}, status=403)

        if self.verify_otp(request, otp_data['secret']):
            await self.update_otp_success(otp_data, access_token, user_data)
            return JsonResponse({"success": "OTP authentication verified"}, status=200)

        await self.update_otp_data(user_id, otp_data)
        return self.password_fail_response(otp_data['attempts'])

    @sync_to_async
    def get_otp_data(self, user_id):
        if not user_id:
            return None
        try:
            otp_secret = OTPSecret.objects.get(user_id=user_id)
            data = {
                'secret': otp_secret.secret,
                'attempts': otp_secret.attempts,
                'last_attempt': otp_secret.last_attempt,
                'is_locked': otp_secret.is_locked,
                'is_verified': otp_secret.is_verified
            }
        except OTPSecret.DoesNotExist:
            return None
        return data

    def password_fail_response(self, attempts):
        return JsonResponse(
            {
                "error": "Incorrect password.",
                "remain_attempts": MAX_ATTEMPTS - attempts
            }, status=400)

    def is_account_locked(self, otp_data, now):
        if otp_data['is_locked']:
            if otp_data['last_attempt'] and (now - otp_data['last_attempt']).total_seconds() > LOCK_ACCOUNT:
                otp_data['is_locked'] = False
                otp_data['attempts'] = 0
                return False
            return True
        return False

    def verify_otp(self, request, secret):
        body = json.loads(request.body.decode('utf-8'))
        otp_code = body.get("input_password")
        return pyotp.TOTP(secret).verify(otp_code)

    @sync_to_async
    def update_otp_success(self, otp_data, access_token, user_data):
        otp_data['attempts'] = 0
        otp_data['is_locked'] = False
        otp_data['is_verified'] = True
        cache.set(f'otp_passed_{access_token}', user_data, timeout=TOKEN_EXPIRES)
        self.update_otp_data(user_data['id'], otp_data)

    @sync_to_async
    def update_otp_data(self, user_id, data):
        """
        OTP 시도 횟수 및 시간 저장
        5회 이상 시도 시 계정 잠금 및 초기화 시간 900초 소요
        """
        OTPSecret.objects.filter(user_id=user_id).update(
            attempts=data['attempts'],
            last_attempt=data['last_attempt'],
            is_locked=data['is_locked'],
            is_verified=data['is_verified']
        )


class Login(View):
    async def get(self, request):
        return HttpResponseRedirect(AUTH_PAGE)
    

class Test(View):
    @login_required
    async def get(self, request):
        return JsonResponse({"hi": "hi"})