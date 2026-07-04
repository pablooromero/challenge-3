from __future__ import annotations

from urllib.parse import urlencode

from app.models import FormPayload


def build_prefilled_url(payload: FormPayload) -> str:
    params: dict[str, str] = {}
    for field in payload.fields:
        if not field.entry_id:
            continue
        if field.field_type == "checkbox":
            if field.value and field.options:
                params[f"entry.{field.entry_id}"] = field.options[0]
            continue
        if field.value is not None:
            params[f"entry.{field.entry_id}"] = str(field.value)

    separator = "&" if "?" in payload.url else "?"
    return f"{payload.url}{separator}{urlencode(params)}"
