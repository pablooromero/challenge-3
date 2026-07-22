from app.models import FormName
from app.sheets import PublicSheetsClient

_GOOD_VENTA = {
    "ID_Cliente": "FIAT-001",
    "Nombre_Cliente": "Carlos Mendoza",
    "Email": "carlos.m@mail.com",
    "Telefono": "54119876543",
    "Modelo_Auto": "Fiat Cronos",
    "Valor_Vehiculo": " $ 18,500,000 ",
    "Tipo_Financiacion": "Crédito Prendario",
}
_GOOD_MORA = {
    "ID_Cliente": "FIAT-001",
    "Nombre_Cliente": "Carlos Mendoza",
    "Valor_Vehiculo": " $ 18,500,000 ",
    "Tipo_Financiacion": "Crédito Prendario",
    "Estado_Pago": "Al Día",
    "Dias_Atraso": "0",
    "Ultimo_Pago_Monto": " $ 450,000 ",
    "Requiere_Cobranza": "No",
}


def test_read_joined_records_merges_tabs(monkeypatch) -> None:
    client = PublicSheetsClient(sheet_id="test")

    def fake_read_sheet(sheet_name: str) -> list[dict[str, str]]:
        return [_GOOD_VENTA] if sheet_name == "Ventas" else [_GOOD_MORA]

    monkeypatch.setattr(client, "read_sheet", fake_read_sheet)
    result = client.read_joined_records()
    assert len(result.records) == 1
    assert result.records[0].venta is not None
    assert result.records[0].mora is not None
    assert result.quarantined == []


def test_malformed_row_is_quarantined_not_crashing(monkeypatch) -> None:
    client = PublicSheetsClient(sheet_id="test")

    def fake_read_sheet(sheet_name: str) -> list[dict[str, str]]:
        if sheet_name == "Ventas":
            # Segunda fila malformada: le faltan columnas requeridas.
            return [_GOOD_VENTA, {"ID_Cliente": "FIAT-002", "Nombre_Cliente": "Ana"}]
        return []

    monkeypatch.setattr(client, "read_sheet", fake_read_sheet)
    result = client.read_joined_records()

    # La corrida no crashea: la fila buena entra, la mala se cuarentena.
    valid_ids = [record.id_cliente for record in result.records]
    assert "FIAT-001" in valid_ids
    assert "FIAT-002" not in valid_ids
    assert len(result.quarantined) == 1
    assert result.quarantined[0].id_cliente == "FIAT-002"
    assert result.quarantined[0].form_name == FormName.VENTAS


def test_fully_empty_rows_are_skipped(monkeypatch) -> None:
    client = PublicSheetsClient(sheet_id="test")

    def fake_read_sheet(sheet_name: str) -> list[dict[str, str]]:
        if sheet_name == "Ventas":
            return [_GOOD_VENTA, {"ID_Cliente": "", "Nombre_Cliente": "", "Email": ""}]
        return []

    monkeypatch.setattr(client, "read_sheet", fake_read_sheet)
    result = client.read_joined_records()
    assert len(result.records) == 1
    assert result.quarantined == []
