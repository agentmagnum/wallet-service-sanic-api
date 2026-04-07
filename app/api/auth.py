from __future__ import annotations

from sqlalchemy import select
from sanic import Blueprint, json

from app.models import User
from app.schemas import LoginRequest
from app.security import create_access_token, verify_password
from app.utils import parse_payload

auth_blueprint = Blueprint("auth", url_prefix="/api/v1/auth")


@auth_blueprint.post("/login")
async def login(request):
    payload = parse_payload(LoginRequest, request.json)

    async with request.app.ctx.session_factory() as session:
        query = select(User).where(User.email == payload.email)
        user = await session.scalar(query)

    if user is None or not verify_password(payload.password, user.password_hash):
        return json({"error": "Invalid email or password"}, status=401)

    token = create_access_token(user, request.app.ctx.settings)
    return json(
        {
            "access_token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
            },
        }
    )

