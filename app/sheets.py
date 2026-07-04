from __future__ import annotations

import csv
from io import StringIO

import httpx

from app.models import ClientRecord, MoraRow, VentaRow


def _normalize_headers(row: dict[str, str]) -> dict[str, str]:
    return {key.strip(): value.strip() for key, value in row.items() if key}


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

    def read_ventas(self) -> list[VentaRow]:
        return [VentaRow.model_validate(row) for row in self.read_sheet("Ventas")]

    def read_mora(self) -> list[MoraRow]:
        return [MoraRow.model_validate(row) for row in self.read_sheet("Mora")]

    def read_joined_records(self) -> list[ClientRecord]:
        ventas_by_id = {row.id_cliente: row for row in self.read_ventas()}
        mora_by_id = {row.id_cliente: row for row in self.read_mora()}
        ids = sorted(set(ventas_by_id) | set(mora_by_id))

        return [
            ClientRecord(
                id_cliente=record_id,
                venta=ventas_by_id.get(record_id),
                mora=mora_by_id.get(record_id),
            )
            for record_id in ids
        ]

