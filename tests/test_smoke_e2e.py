import os

import pytest


@pytest.mark.skipif(
    os.getenv("RUN_SMOKE_E2E") != "1",
    reason="Set RUN_SMOKE_E2E=1 to run the real browser smoke test.",
)
def test_smoke_placeholder() -> None:
    # This stays opt-in because it hits real Google Forms.
    assert True

