import os

import pytest


def require_live_env(required: list[str] | None = None) -> None:
    live_flag = (os.getenv("GMO_LIVE_TESTS") or "").strip().lower()
    if live_flag not in {"1", "true", "yes", "on"}:
        pytest.skip("Live tests are disabled. Set GMO_LIVE_TESTS=true to enable.")

    required = required or []
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing environment variables: {', '.join(missing)}")
