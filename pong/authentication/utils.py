from django.db import transaction, IntegrityError
from .models import User, OTPSecret
from .crypto import AESCipher
from .constants import TOKEN_EXPIRES
import logging


logger = logging.getLogger(__name__)

async def get_user_data(user_id):
    """
    cache에 저장해둔 user_data를 조회한다.
    없을 경우 db에서 꺼내온 후 cache에 저장하고
    값을 반환한다.
    """
    user_data = await get_user_data_from_cache(user_id)
    if not user_data:
        user_data = await get_user_data_from_db(user_id)
        if user_data:
            decrypt_secret(user_data)
            await cache.aset(f"user_data_{user_id}", user_data, TOKEN_EXPIRES)
    return user_data

def decrypt_secret(user_data):
    secret = AESCipher.decrypt(user_data["encrypted_secret"])
    del user_data["encrypted_secret"]
    user_data["secret"] = secret
    return user_data

async def get_user_data_from_cache(user_id):
    return await cache.aget(f"user_data_{user_id}")

    user_data = User.objects.annotate(
@sync_to_async
def get_user_data_from_db(user_id):
        encrypted_secret=F("otpsecret__encrypted_secret"),
        is_verified=F("otpsecret__is_verified"),
        need_otp=F("otpsecret__need_otp")
    ).values("login", "email", "encrypted_secret", "is_verified", "need_otp").first()

    if not user_data:
        logger.warning(f"User with id {user_id} not found in database")
        return None
    
    return user_data