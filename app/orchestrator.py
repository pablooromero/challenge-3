from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.forms.base import FormFillError
from app.forms.form_mora import MoraFormDriver
from app.forms.form_ventas import VentasFormDriver
from app.integrity import assert_required_fields_present
from app.models import FormName, FormPayload, QuarantinedRecord, SubmissionStatus
from app.post_submit import submit_via_form_response
from app.state import SubmissionStateStore


class SubmissionUnknownError(RuntimeError):
    """Raised when submit may have happened but confirmation was not observed."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((FormFillError, TimeoutError)),
    reraise=True,
)
def _submit_with_retry(
    payload: FormPayload,
    headless: bool,
    timeout_ms: int,
    evidence_dir: Path,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 2000},
            record_video_dir=str(evidence_dir / "videos"),
        )
        page = context.new_page()
        try:
            if payload.form_name == FormName.VENTAS:
                driver = VentasFormDriver(page, timeout_ms)
            else:
                driver = MoraFormDriver(page, timeout_ms)
            driver.submit_payload(payload, evidence_dir)
        except Exception as exc:
            if "Se registró tu respuesta" in page.content():
                raise SubmissionUnknownError(str(exc)) from exc
            raise
        finally:
            context.close()
            browser.close()


def process_payloads(
    payloads: list[FormPayload],
    state_store: SubmissionStateStore,
    current_state: dict,
    headless: bool,
    timeout_ms: int,
    evidence_dir: Path,
    mapping: dict,
    allow_form_post_fallback: bool,
    verify_ssl: bool,
) -> tuple[dict, list[QuarantinedRecord]]:
    quarantined: list[QuarantinedRecord] = []

    for payload in payloads:
        state_key = state_store.make_key(payload.id_cliente, payload.form_name)
        existing = current_state.get(state_key)
        if existing and existing.status == SubmissionStatus.CONFIRMED:
            continue
        if existing and existing.status == SubmissionStatus.UNKNOWN:
            continue

        try:
            assert_required_fields_present(payload)
            _submit_with_retry(payload, headless=headless, timeout_ms=timeout_ms, evidence_dir=evidence_dir)
            current_state = state_store.upsert(
                current_state,
                payload.id_cliente,
                payload.form_name,
                SubmissionStatus.CONFIRMED,
            )
        except SubmissionUnknownError as exc:
            current_state = state_store.upsert(
                current_state,
                payload.id_cliente,
                payload.form_name,
                SubmissionStatus.UNKNOWN,
                reason=str(exc),
            )
        except Exception as exc:
            if allow_form_post_fallback:
                form_config = mapping["forms"][payload.form_name.value]
                submit_via_form_response(
                    payload=payload,
                    form_id=form_config["form_id"],
                    page_history=form_config["page_history"],
                    verify_ssl=verify_ssl,
                )
                current_state = state_store.upsert(
                    current_state,
                    payload.id_cliente,
                    payload.form_name,
                    SubmissionStatus.CONFIRMED,
                    reason=f"http_fallback_after_browser_error: {exc}",
                )
            else:
                current_state = state_store.upsert(
                    current_state,
                    payload.id_cliente,
                    payload.form_name,
                    SubmissionStatus.QUARANTINED,
                    reason=str(exc),
                )
                quarantined.append(
                    QuarantinedRecord(
                        id_cliente=payload.id_cliente,
                        form_name=payload.form_name,
                        reason=str(exc),
                    )
                )

    return current_state, quarantined
