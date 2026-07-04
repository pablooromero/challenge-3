from __future__ import annotations

import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from app.models import (
    ClientRecord,
    FormName,
    FormPayload,
    MoraRow,
    NormalizedField,
    QuarantinedRecord,
    VentaRow,
)


def load_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.lower().split())


def normalize_currency(value: str) -> str:
    cleaned = normalize_text(value).replace("$", "").replace(",", "").strip()
    if cleaned == "-":
        return "0"
    return cleaned


def normalize_checkbox(value: str) -> bool:
    return slugify(value) in {"si", "si activar protocolo de cobranza legal", "true", "yes"}


def match_option(value: str, options: list[str]) -> str | None:
    desired = slugify(value)
    for option in options:
        if slugify(option) == desired:
            return option
    return None


def transform_value(transform: str | None, value: str, options: list[str]) -> str | bool:
    if transform == "currency":
        return normalize_currency(value)
    if transform == "option_match":
        matched = match_option(value, options)
        if matched is None:
            raise ValueError(f"No option match found for '{value}'")
        return matched
    if transform == "checkbox_bool":
        return normalize_checkbox(value)
    return normalize_text(value)


def _build_fields(
    mapping_fields: list[dict[str, Any]],
    source: dict[str, str],
) -> list[NormalizedField]:
    normalized_fields: list[NormalizedField] = []
    for field in mapping_fields:
        raw_value = source.get(field["source"], "")
        options = field.get("options", [])
        value = transform_value(field.get("transform"), raw_value, options)
        normalized_fields.append(
            NormalizedField(
                field_key=field["name"],
                label=field["label"],
                field_type=field["type"],
                required=field.get("required", False),
                page=field.get("page", 1),
                value=value,
                options=options,
                entry_id=field.get("entry_id"),
            )
        )
    return normalized_fields


def build_form_payload(
    form_name: FormName,
    record_id: str,
    source_row: VentaRow | MoraRow,
    mapping: dict[str, Any],
) -> FormPayload:
    form_config = deepcopy(mapping["forms"][form_name.value])
    source_data = source_row.model_dump(by_alias=True)
    fields = _build_fields(form_config["fields"], source_data)
    return FormPayload(
        form_name=form_name,
        id_cliente=record_id,
        url=form_config["url"],
        title=form_config["title"],
        fields=fields,
    )


def build_payloads_for_record(
    record: ClientRecord,
    mapping: dict[str, Any],
) -> tuple[list[FormPayload], list[QuarantinedRecord]]:
    payloads: list[FormPayload] = []
    quarantined: list[QuarantinedRecord] = []

    if record.venta is not None:
        try:
            payloads.append(build_form_payload(FormName.VENTAS, record.id_cliente, record.venta, mapping))
        except ValueError as exc:
            quarantined.append(
                QuarantinedRecord(
                    id_cliente=record.id_cliente,
                    form_name=FormName.VENTAS,
                    reason=str(exc),
                )
            )

    if record.mora is not None:
        try:
            payloads.append(build_form_payload(FormName.MORA, record.id_cliente, record.mora, mapping))
        except ValueError as exc:
            quarantined.append(
                QuarantinedRecord(
                    id_cliente=record.id_cliente,
                    form_name=FormName.MORA,
                    reason=str(exc),
                )
            )

    return payloads, quarantined
