from __future__ import annotations

import csv
from io import StringIO
from typing import Type

import httpx
from pydantic import ValidationError

from app.models import (
    ClientRecord,
    FormName,
    IngestResult,
    MoraRow,
    QuarantinedRecord,
    SheetRowBase,
    VentaRow,
)


def _normalize_headers(row: dict[str, str | None]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in row.items():
        if not key:
            continue
        if isinstance(value, str):
            cleaned[key.strip()] = value.strip()
        elif value is None:
            cleaned[key.strip()] = ""
        else:
            cleaned[key.strip()] = str(value)
    return cleaned


class PublicSheetsClient:
    def __init__(self, sheet_id: str, verify_ssl: bool = True) -> None:
        self.sheet_id = sheet_id
        self.verify_ssl = verify_ssl

    def _fetch_csv(self, sheet_name: str) -> str:
        url = (
            f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq"
            f"?tqx=out:csv&sheet={sheet_name}"
        )
        response = httpx.get(url, timeout=20.0, verify=self.verify_ssl)
        response.raise_for_status()
        return response.text

    def read_sheet(self, sheet_name: str) -> list[dict[str, str]]:
        content = self._fetch_csv(sheet_name)
        reader = csv.DictReader(StringIO(content))
        return [_normalize_headers(row) for row in reader]

    def _parse_rows(
        self,
        sheet_name: str,
        model: Type[SheetRowBase],
        form_name: FormName,
    ) -> tuple[list[SheetRowBase], list[QuarantinedRecord]]:
        """Parsea fila por fila: una fila invalida se cuarentena, no rompe la corrida."""
        parsed: list[SheetRowBase] = []
        errors: list[QuarantinedRecord] = []
        for index, raw in enumerate(self.read_sheet(sheet_name)):
            if not any(value for value in raw.values()):
                continue  # fila totalmente vacia (artefacto de CSV)
            try:
                parsed.append(model.model_validate(raw))
            except ValidationError as exc:
                row_ref = raw.get("ID_Cliente") or f"{sheet_name}:row{index + 2}"
                bad_fields = ", ".join(
                    str(err["loc"][0]) for err in exc.errors() if err.get("loc")
                )
                errors.append(
                    QuarantinedRecord(
                        id_cliente=row_ref,
                        form_name=form_name,
                        reason=f"parse_error invalid/missing fields: {bad_fields}",
                    )
                )
        return parsed, errors

    def read_joined_records(self) -> IngestResult:
        ventas, ventas_errors = self._parse_rows("Ventas", VentaRow, FormName.VENTAS)
        mora, mora_errors = self._parse_rows("Mora", MoraRow, FormName.MORA)

        ventas_by_id = {row.id_cliente: row for row in ventas if row.id_cliente}
        mora_by_id = {row.id_cliente: row for row in mora if row.id_cliente}
        ids = sorted(set(ventas_by_id) | set(mora_by_id))

        records = [
            ClientRecord(
                id_cliente=record_id,
                venta=ventas_by_id.get(record_id),  # type: ignore[arg-type]
                mora=mora_by_id.get(record_id),  # type: ignore[arg-type]
            )
            for record_id in ids
        ]
        return IngestResult(records=records, quarantined=ventas_errors + mora_errors)
