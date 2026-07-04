from __future__ import annotations

from collections import Counter

from app.models import QuarantinedRecord, SubmissionRecord


def render_report(
    state: dict[str, SubmissionRecord],
    quarantined: list[QuarantinedRecord],
) -> str:
    counter = Counter(record.status.value for record in state.values())
    lines = [
        "Run summary:",
        f"- confirmed_prefill_browser: {counter.get('confirmed_prefill_browser', 0)}",
        f"- confirmed_http_fallback: {counter.get('confirmed_http_fallback', 0)}",
        f"- unknown: {counter.get('unknown', 0)}",
        f"- quarantined: {counter.get('quarantined', 0) + len(quarantined)}",
    ]
    if quarantined:
        lines.append("Quarantine details:")
        for item in quarantined:
            lines.append(f"- {item.id_cliente} / {item.form_name.value}: {item.reason}")
    return "\n".join(lines)
