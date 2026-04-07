from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

MONEY_QUANT = Decimal("0.01")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be empty")
        return value


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be empty")
        return value

    @model_validator(mode="after")
    def ensure_not_empty(self) -> "UserUpdateRequest":
        if self.email is None and self.full_name is None and self.password is None:
            raise ValueError("At least one field must be provided")
        return self


class PaymentWebhookRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=255)
    account_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    amount: Decimal
    signature: str = Field(min_length=64, max_length=64)

    @field_validator("transaction_id", "signature")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be empty")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        normalized = value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        if normalized <= 0:
            raise ValueError("Amount must be greater than zero")
        return normalized

