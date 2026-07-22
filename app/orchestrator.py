from __future__ import annotations

from pathlib import Path
from typing import Callable

from playwright.sync_api import sync_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.forms.base import CONFIRMATION_PATTERN
from app.forms.form_mora import MoraFormDriver
from app.forms.form_ventas import VentasFormDriver
from app.integrity import assert_required_fields_present
from app.models import FormName, FormPayload, QuarantinedRecord, SubmissionStatus
from app.post_submit import submit_via_form_response
from app.state import SubmissionStateStore


class PreSubmitError(RuntimeError):
    """La preparacion fallo antes de tocar el boton Enviar.

    Como no hubo envio, es seguro reintentar y, si se agotan los reintentos,
    caer al fallback HTTP sin riesgo de duplicar.
    """


def _looks_confirmed(page) -> bool:
    """Senal robusta de que el envio ocurrio, con multiples marcadores."""
    try:
        if "formResponse" in page.url:
            return True
        content = page.content()
    except Exception:  # noqa: BLE001 - si no podemos leer la pagina, asumimos no confirmado
        return False
    return bool(CONFIRMATION_PATTERN.search(content))


def _driver_for(page, form_name: FormName, timeout_ms: int):
    if form_name == FormName.VENTAS:
        return VentasFormDriver(page, timeout_ms)
    return MoraFormDriver(page, timeout_ms)


def _run_single_attempt(driver, page, payload, evidence_dir) -> SubmissionStatus:
    """Un intento: prepara (retryable) y luego envia EXACTAMENTE una vez.

    - Cualquier fallo antes de Enviar se normaliza a PreSubmitError (reintentable).
    - Cualquier fallo despues de Enviar nunca se reintenta: se decide entre
      CONFIRMED (si la pagina muestra confirmacion) o UNKNOWN, evitando el
      doble envio.
    """
    try:
        driver.prepare(payload, evidence_dir)
    except Exception as exc:  # noqa: BLE001
        raise PreSubmitError(str(exc)) from exc

    try:
        driver.submit_and_confirm(payload, evidence_dir)
        return SubmissionStatus.CONFIRMED_PREFILL_BROWSER
    except Exception:  # noqa: BLE001 - cruzamos el boundary del submit: nunca reenviar
        if _looks_confirmed(page):
            return SubmissionStatus.CONFIRMED_PREFILL_BROWSER
        return SubmissionStatus.UNKNOWN


def _with_retry(attempt: Callable[[], SubmissionStatus]) -> SubmissionStatus:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(PreSubmitError),
        reraise=True,
    )
    def _runner() -> SubmissionStatus:
        return attempt()

    return _runner()


def _attempt(browser, payload: FormPayload, timeout_ms: int, evidence_dir: Path) -> SubmissionStatus:
    context = browser.new_context(
        viewport={"width": 1280, "height": 2000},
        record_video_dir=str(Path(evidence_dir) / "videos"),
    )
    page = context.new_page()
    try:
        driver = _driver_for(page, payload.form_name, timeout_ms)
        return _run_single_attempt(driver, page, payload, evidence_dir)
    finally:
        context.close()


def run_browser_submission(
    payload: FormPayload,
    headless: bool,
    timeout_ms: int,
    evidence_dir: Path,
) -> SubmissionStatus:
    """Devuelve CONFIRMED_PREFILL_BROWSER o UNKNOWN; levanta PreSubmitError si
    la preparacion fallo tras los reintentos (sin haber enviado nunca)."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        try:
            return _with_retry(lambda: _attempt(browser, payload, timeout_ms, evidence_dir))
        finally:
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
        if existing and existing.is_confirmed:
            continue
        if existing and existing.status == SubmissionStatus.UNKNOWN:
            continue  # ambiguo: no se reintenta automaticamente

        # Gate de validacion: datos invalidos se cuarentenan y NUNCA se envian
        # (ni por browser ni por fallback HTTP).
        try:
            assert_required_fields_present(payload)
        except ValueError as exc:
            current_state = state_store.upsert(
                current_state, payload.id_cliente, payload.form_name,
                SubmissionStatus.QUARANTINED, reason=str(exc),
            )
            quarantined.append(
                QuarantinedRecord(id_cliente=payload.id_cliente, form_name=payload.form_name, reason=str(exc))
            )
            continue

        try:
            status = run_browser_submission(
                payload, headless=headless, timeout_ms=timeout_ms, evidence_dir=evidence_dir
            )
            reason = (
                "prefilled_url_browser"
                if status == SubmissionStatus.CONFIRMED_PREFILL_BROWSER
                else "post_submit_unconfirmed"
            )
            current_state = state_store.upsert(
                current_state, payload.id_cliente, payload.form_name, status, reason=reason
            )
        except PreSubmitError as exc:
            # El browser nunca llego a enviar -> el fallback HTTP es seguro (no duplica).
            current_state, quarantined = _handle_presubmit_failure(
                payload, exc, state_store, current_state, quarantined,
                mapping, allow_form_post_fallback, verify_ssl,
            )

    return current_state, quarantined


def _handle_presubmit_failure(
    payload, exc, state_store, current_state, quarantined,
    mapping, allow_form_post_fallback, verify_ssl,
):
    if not allow_form_post_fallback:
        current_state = state_store.upsert(
            current_state, payload.id_cliente, payload.form_name,
            SubmissionStatus.QUARANTINED, reason=str(exc),
        )
        quarantined.append(
            QuarantinedRecord(id_cliente=payload.id_cliente, form_name=payload.form_name, reason=str(exc))
        )
        return current_state, quarantined

    form_config = mapping["forms"][payload.form_name.value]
    try:
        submit_via_form_response(
            payload=payload,
            form_id=form_config["form_id"],
            page_history=form_config["page_history"],
            verify_ssl=verify_ssl,
        )
        current_state = state_store.upsert(
            current_state, payload.id_cliente, payload.form_name,
            SubmissionStatus.CONFIRMED_HTTP_FALLBACK,
            reason=f"http_fallback_after_browser_error: {exc}",
        )
    except Exception as fallback_exc:  # noqa: BLE001 - el fallback fallo: cuarentena, no crashea la corrida
        reason = f"http_fallback_failed: {fallback_exc}"
        current_state = state_store.upsert(
            current_state, payload.id_cliente, payload.form_name,
            SubmissionStatus.QUARANTINED, reason=reason,
        )
        quarantined.append(
            QuarantinedRecord(id_cliente=payload.id_cliente, form_name=payload.form_name, reason=reason)
        )
    return current_state, quarantined
