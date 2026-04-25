from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id")
        response = await call_next(request)
        if request.state.request_id:
            response.headers["x-request-id"] = request.state.request_id
        return response
