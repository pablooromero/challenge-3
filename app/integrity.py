from __future__ import annotations

from app.models import FormPayload


def assert_required_fields_present(payload: FormPayload) -> None:
    for field in payload.fields:
        if not field.required:
            continue
        if field.value in (None, ""):
            raise ValueError(f"Required field '{field.label}' is empty")

