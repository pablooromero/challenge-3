"""Smoke E2E real (opt-in): envia 1 registro real a ambos Google Forms.

Se salta por defecto porque genera respuestas reales. Activar con:
    RUN_SMOKE_E2E=1 HEADLESS=true PYTHONPATH=. python3 -m pytest tests/test_smoke_e2e.py -q
"""
import os

import pytest

from app.config import get_settings
from app.models import SubmissionStatus
from app.normalize import build_payloads_for_record, load_mapping
from app.orchestrator import run_browser_submission
from app.sheets import PublicSheetsClient


@pytest.mark.skipif(
    os.getenv("RUN_SMOKE_E2E") != "1",
    reason="Set RUN_SMOKE_E2E=1 to run the real browser E2E (submits to real Google Forms).",
)
def test_smoke_submits_first_record_to_both_forms(tmp_path) -> None:
    settings = get_settings()
    mapping = load_mapping(settings.mapping_file)
    client = PublicSheetsClient(sheet_id=settings.sheet_id, verify_ssl=settings.sheets_verify_ssl)

    ingest = client.read_joined_records()
    assert ingest.records, "No se leyeron registros del Sheet"

    record = ingest.records[0]
    payloads, quarantined = build_payloads_for_record(record, mapping)
    assert payloads, "No se construyeron payloads para el primer registro"
    assert not quarantined, f"Cuarentena inesperada: {quarantined}"

    for payload in payloads:
        status = run_browser_submission(
            payload,
            headless=True,
            timeout_ms=settings.playwright_timeout_ms,
            evidence_dir=tmp_path,
        )
        assert status == SubmissionStatus.CONFIRMED_PREFILL_BROWSER, f"{payload.form_name.value} -> {status}"
