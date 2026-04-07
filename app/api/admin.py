from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sanic import Blueprint, empty, json

from app.errors import ApiError
from app.models import User, UserRole
from app.pagination import parse_pagination
from app.schemas import UserCreateRequest, UserUpdateRequest
from app.security import hash_password_async, require_roles
from app.utils import format_money, parse_payload

admin_blueprint = Blueprint("admin", url_prefix="/api/v1/admin")


def _serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "accounts": [
            {
                "id": account.id,
                "balance": format_money(account.balance),
            }
            for account in sorted(user.accounts, key=lambda account: account.id)
        ],
    }


@admin_blueprint.get("/users")
@require_roles(UserRole.ADMIN)
async def list_users(request):
    pagination = parse_pagination(request, default_limit=100, max_limit=500)

    async with request.app.ctx.session_factory() as session:
        query = (
            select(User)
            .options(selectinload(User.accounts))
            .where(User.role == UserRole.USER)
            .order_by(User.id.asc())
        )
        if pagination.limit is not None:
            query = query.offset(pagination.offset).limit(pagination.limit)
        users = list(await session.scalars(query))

    return json(
        {
            "items": [_serialize_user(user) for user in users],
            "pagination": pagination.to_meta(returned_count=len(users)),
        }
    )


@admin_blueprint.get("/users/<user_id:int>")
@require_roles(UserRole.ADMIN)
async def get_user(request, user_id: int):
    async with request.app.ctx.session_factory() as session:
        query = (
            select(User)
            .options(selectinload(User.accounts))
            .where(User.id == user_id, User.role == UserRole.USER)
        )
        user = await session.scalar(query)

    if user is None:
        raise ApiError(status=404, message="User not found")

    return json(_serialize_user(user))


@admin_blueprint.post("/users")
@require_roles(UserRole.ADMIN)
async def create_user(request):
    payload = parse_payload(UserCreateRequest, request.json)

    async with request.app.ctx.session_factory() as session:
        existing_user = await session.scalar(select(User).where(User.email == payload.email))
        if existing_user is not None:
            raise ApiError(status=409, message="User with this email already exists")

        new_user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=await hash_password_async(payload.password),
            role=UserRole.USER,
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

    return json(
        {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role.value,
            "accounts": [],
        },
        status=201,
    )


@admin_blueprint.patch("/users/<user_id:int>")
@require_roles(UserRole.ADMIN)
async def update_user(request, user_id: int):
    payload = parse_payload(UserUpdateRequest, request.json)

    async with request.app.ctx.session_factory() as session:
        query = (
            select(User)
            .options(selectinload(User.accounts))
            .where(User.id == user_id, User.role == UserRole.USER)
        )
        user = await session.scalar(query)

        if user is None:
            raise ApiError(status=404, message="User not found")

        if payload.email is not None and payload.email != user.email:
            email_owner = await session.scalar(select(User).where(User.email == payload.email))
            if email_owner is not None:
                raise ApiError(status=409, message="User with this email already exists")
            user.email = payload.email

        if payload.full_name is not None:
            user.full_name = payload.full_name

        if payload.password is not None:
            user.password_hash = await hash_password_async(payload.password)

        await session.commit()
        await session.refresh(user)

    return json(_serialize_user(user))


@admin_blueprint.delete("/users/<user_id:int>")
@require_roles(UserRole.ADMIN)
async def delete_user(request, user_id: int):
    async with request.app.ctx.session_factory() as session:
        user = await session.scalar(select(User).where(User.id == user_id, User.role == UserRole.USER))
        if user is None:
            raise ApiError(status=404, message="User not found")

        await session.delete(user)
        await session.commit()

    return empty(status=204)
