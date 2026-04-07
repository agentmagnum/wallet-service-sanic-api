from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ValidationError

from app.errors import ApiError

MONEY_QUANT = Decimal("0.01")


def parse_payload(model_cls: type[BaseModel], payload: object) -> BaseModel:
    try:
        return model_cls.model_validate(payload or {})
    except ValidationError as exc:
        raise ApiError(
            status=400,
            message="Validation error",
            details=exc.errors(include_url=False, include_context=False),
        ) from exc


def format_money(value: Decimal) -> str:
    normalized = value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    return f"{normalized:.2f}"


def isoformat_or_none(value) -> str | None:
    return value.isoformat() if value is not None else None

