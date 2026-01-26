from __future__ import annotations

from typing import Any


class GmoCoinError(RuntimeError):
    """Base error for GMO Coin client failures."""


class GmoCoinApiError(GmoCoinError):
    """Raised when the API returns a non-success status payload."""

    def __init__(self, status: int | None, messages: list[dict[str, Any]] | None, payload: Any):
        self.status = status
        self.messages = messages or []
        self.payload = payload
        message = self._build_message()
        super().__init__(message)

    def _build_message(self) -> str:
        if not self.messages:
            return "GMO Coin API returned an error response"
        parts = []
        for item in self.messages:
            code = item.get("message_code")
            text = item.get("message_string")
            if code or text:
                parts.append(f"{code or 'UNKNOWN'}: {text or 'Unknown error'}")
        if not parts:
            return "GMO Coin API returned an error response"
        return "; ".join(parts)


class GmoCoinHttpError(GmoCoinError):
    """Raised when the HTTP layer fails or returns a non-success status."""

    def __init__(self, status_code: int | None, message: str, payload: Any | None = None):
        self.status_code = status_code
        self.payload = payload
        super().__init__(message)
