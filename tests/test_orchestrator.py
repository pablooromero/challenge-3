"""Tests del retry seguro: nunca reenviar tras cruzar el submit (fix doble envio)."""
from __future__ import annotations

import pytest

from app.models import SubmissionStatus
from app.orchestrator import PreSubmitError, _run_single_attempt, _with_retry


class FakePage:
    def __init__(self, url: str = "https://docs.google.com/forms/.../viewform", content: str = "") -> None:
        self._url = url
        self._content = content

    @property
    def url(self) -> str:
        return self._url

    def content(self) -> str:
        return self._content


class FakeDriver:
    def __init__(self, prepare_exc: Exception | None = None, submit_exc: Exception | None = None) -> None:
        self.prepare_exc = prepare_exc
        self.submit_exc = submit_exc
        self.prepare_calls = 0
        self.submit_calls = 0

    def prepare(self, payload, evidence_dir) -> None:
        self.prepare_calls += 1
        if self.prepare_exc:
            raise self.prepare_exc

    def submit_and_confirm(self, payload, evidence_dir) -> None:
        self.submit_calls += 1
        if self.submit_exc:
            raise self.submit_exc


def test_prepare_failure_raises_presubmit_and_never_submits() -> None:
    driver = FakeDriver(prepare_exc=RuntimeError("timeout esperando el campo"))
    with pytest.raises(PreSubmitError):
        _run_single_attempt(driver, FakePage(), payload=None, evidence_dir=None)
    assert driver.submit_calls == 0  # nunca se apreto Enviar


def test_post_submit_failure_without_confirmation_is_unknown_and_submits_once() -> None:
    driver = FakeDriver(submit_exc=RuntimeError("confirmation timeout"))
    page = FakePage(content="<html>algo salio mal</html>")
    status = _run_single_attempt(driver, page, payload=None, evidence_dir=None)
    assert status == SubmissionStatus.UNKNOWN
    assert driver.submit_calls == 1  # se envio una sola vez, no se reintento


def test_post_submit_failure_with_confirmation_text_is_confirmed() -> None:
    driver = FakeDriver(submit_exc=RuntimeError("elemento stale tras confirmar"))
    page = FakePage(content="... Se registró tu respuesta ...")
    status = _run_single_attempt(driver, page, payload=None, evidence_dir=None)
    assert status == SubmissionStatus.CONFIRMED_PREFILL_BROWSER
    assert driver.submit_calls == 1


def test_confirmed_by_form_response_url() -> None:
    driver = FakeDriver(submit_exc=RuntimeError("timeout de wait_for_confirmation"))
    page = FakePage(url="https://docs.google.com/forms/d/e/xxx/formResponse", content="")
    assert _run_single_attempt(driver, page, None, None) == SubmissionStatus.CONFIRMED_PREFILL_BROWSER


def test_retry_reattempts_presubmit_then_succeeds() -> None:
    calls = {"n": 0}

    def attempt() -> SubmissionStatus:
        calls["n"] += 1
        if calls["n"] < 3:
            raise PreSubmitError("preparacion fallo")
        return SubmissionStatus.CONFIRMED_PREFILL_BROWSER

    assert _with_retry(attempt) == SubmissionStatus.CONFIRMED_PREFILL_BROWSER
    assert calls["n"] == 3


def test_retry_does_not_reattempt_unknown() -> None:
    calls = {"n": 0}

    def attempt() -> SubmissionStatus:
        calls["n"] += 1
        return SubmissionStatus.UNKNOWN

    assert _with_retry(attempt) == SubmissionStatus.UNKNOWN
    assert calls["n"] == 1  # UNKNOWN post-submit no se reintenta
