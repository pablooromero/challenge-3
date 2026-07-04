from __future__ import annotations

import httpx

from app.models import FormPayload


class FormPostFallbackError(RuntimeError):
    """Raised when direct formResponse submission fails."""


def build_form_response_payload(payload: FormPayload, page_history: str) -> dict[str, str]:
    data = {
        "fvv": "1",
        "draftResponse": "[]",
        "pageHistory": page_history,
    }
    for field in payload.fields:
        if not field.entry_id:
            continue
        key = f"entry.{field.entry_id}"
        if field.field_type == "checkbox":
            if field.value and field.options:
                data[key] = field.options[0]
            continue
        if field.value is not None:
            data[key] = str(field.value)
    return data


def submit_via_form_response(
    payload: FormPayload,
    form_id: str,
    page_history: str,
    verify_ssl: bool,
) -> None:
    url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"
    response = httpx.post(
        url,
        data=build_form_response_payload(payload, page_history),
        follow_redirects=True,
        timeout=20.0,
        verify=verify_ssl,
    )
    response.raise_for_status()
    if "Se registró tu respuesta" not in response.text:
        raise FormPostFallbackError("Direct formResponse fallback did not return confirmation text")

