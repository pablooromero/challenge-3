from __future__ import annotations

from app.config import get_settings
from app.normalize import build_payloads_for_record, load_mapping
from app.orchestrator import process_payloads
from app.report import render_report
from app.sheets import PublicSheetsClient
from app.state import SubmissionStateStore


def main() -> None:
    settings = get_settings()
    mapping = load_mapping(settings.mapping_file)
    sheet_client = PublicSheetsClient(
        sheet_id=settings.sheet_id,
        verify_ssl=settings.sheets_verify_ssl,
    )
    ingest = sheet_client.read_joined_records()
    records = ingest.records
    state_store = SubmissionStateStore(settings.state_file)
    state = state_store.load()
    quarantined = list(ingest.quarantined)
    payloads = []

    for record in records:
        record_payloads, record_quarantine = build_payloads_for_record(record, mapping)
        payloads.extend(record_payloads)
        quarantined.extend(record_quarantine)

    state, runtime_quarantine = process_payloads(
        payloads=payloads,
        state_store=state_store,
        current_state=state,
        headless=settings.headless,
        timeout_ms=settings.playwright_timeout_ms,
        evidence_dir=settings.evidence_dir,
        mapping=mapping,
        allow_form_post_fallback=settings.allow_form_post_fallback,
        verify_ssl=settings.sheets_verify_ssl,
    )
    quarantined.extend(runtime_quarantine)
    print(render_report(state, quarantined))


if __name__ == "__main__":
    main()
