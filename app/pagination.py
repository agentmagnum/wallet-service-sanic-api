from __future__ import annotations

from dataclasses import dataclass

from sanic import Request

from app.errors import ApiError


@dataclass(frozen=True)
class PaginationParams:
    limit: int | None
    offset: int
    requested: bool

    def to_meta(self, returned_count: int) -> dict[str, int | bool | None]:
        return {
            "applied": self.requested,
            "limit": self.limit,
            "offset": self.offset,
            "returned": returned_count,
        }


def parse_pagination(
    request: Request,
    *,
    default_limit: int = 100,
    max_limit: int = 500,
) -> PaginationParams:
    raw_limit = request.args.get("limit")
    raw_offset = request.args.get("offset")

    if raw_limit is None and raw_offset is None:
        return PaginationParams(limit=None, offset=0, requested=False)

    limit = default_limit if raw_limit is None else _parse_int(raw_limit, field_name="limit")
    offset = 0 if raw_offset is None else _parse_int(raw_offset, field_name="offset")

    if limit <= 0:
        raise ApiError(status=400, message="Query parameter 'limit' must be greater than zero")
    if limit > max_limit:
        raise ApiError(
            status=400,
            message=f"Query parameter 'limit' must be less than or equal to {max_limit}",
        )
    if offset < 0:
        raise ApiError(status=400, message="Query parameter 'offset' must be zero or greater")

    return PaginationParams(limit=limit, offset=offset, requested=True)


def _parse_int(raw_value: str, *, field_name: str) -> int:
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ApiError(status=400, message=f"Query parameter '{field_name}' must be an integer") from exc

