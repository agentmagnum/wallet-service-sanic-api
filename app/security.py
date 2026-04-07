from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from functools import wraps

import jwt
from sanic import Request

from app.config import Settings
from app.errors import ApiError
from app.models import User, UserRole

PBKDF2_NAME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390000
PBKDF2_SALT_BYTES = 16


class AuthContext:
    def __init__(self, user_id: int, email: str, full_name: str, role: UserRole) -> None:
        self.user_id = user_id
        self.email = email
        self.full_name = full_name
        self.role = role

    def to_dict(self) -> dict[str, str | int]:
        return {
            "id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
        }


def hash_password(password: str) -> str:
    salt = os.urandom(PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_NAME}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if algorithm != PBKDF2_NAME:
        return False

    expected = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(expected.hex(), digest_hex)


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(verify_password, password, password_hash)


def create_access_token(user: User, settings: Settings) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(status=401, message="Access token expired") from exc
    except jwt.PyJWTError as exc:
        raise ApiError(status=401, message="Invalid access token") from exc
    return payload


def extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        raise ApiError(status=401, message="Authorization header must use Bearer token")
    return auth_header[len(prefix) :].strip()


def require_roles(*roles: UserRole):
    allowed_roles = {role.value for role in roles}

    def decorator(handler):
        @wraps(handler)
        async def wrapped(request: Request, *args, **kwargs):
            token = extract_bearer_token(request)
            payload = decode_access_token(token, request.app.ctx.settings)
            user_id = payload.get("sub")
            email = payload.get("email")
            full_name = payload.get("full_name")
            role_value = payload.get("role")

            if user_id is None:
                raise ApiError(status=401, message="Invalid access token payload")

            if role_value is None:
                raise ApiError(status=401, message="Invalid access token payload")

            try:
                role = UserRole(role_value)
            except ValueError as exc:
                raise ApiError(status=401, message="Invalid access token payload") from exc

            if email is None or full_name is None:
                async with request.app.ctx.session_factory() as session:
                    user = await session.get(User, int(user_id))

                if user is None:
                    raise ApiError(status=401, message="User from token was not found")

                email = user.email
                full_name = user.full_name
                role = user.role

            if allowed_roles and role.value not in allowed_roles:
                raise ApiError(status=403, message="You do not have permission to access this resource")

            request.ctx.current_user = AuthContext(
                user_id=int(user_id),
                email=email,
                full_name=full_name,
                role=role,
            )
            return await handler(request, *args, **kwargs)

        return wrapped

    return decorator


def build_webhook_signature(payload: dict[str, object], secret_key: str) -> str:
    signature_parts = [
        str(payload["account_id"]),
        str(payload["amount"]),
        str(payload["transaction_id"]),
        str(payload["user_id"]),
        secret_key,
    ]
    raw_value = "".join(signature_parts)
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()
