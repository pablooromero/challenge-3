from app.sheets import PublicSheetsClient


def test_read_joined_records_merges_tabs(monkeypatch) -> None:
    client = PublicSheetsClient(sheet_id="test")

    def fake_read_sheet(sheet_name: str) -> list[dict[str, str]]:
        if sheet_name == "Ventas":
            return [
                {
                    "ID_Cliente": "FIAT-001",
                    "Nombre_Cliente": "Carlos Mendoza",
                    "Email": "carlos.m@mail.com",
                    "Telefono": "54119876543",
                    "Modelo_Auto": "Fiat Cronos",
                    "Valor_Vehiculo": " $ 18,500,000 ",
                    "Tipo_Financiacion": "Crédito Prendario",
                }
            ]
        return [
            {
                "ID_Cliente": "FIAT-001",
                "Nombre_Cliente": "Carlos Mendoza",
                "Valor_Vehiculo": " $ 18,500,000 ",
                "Tipo_Financiacion": "Crédito Prendario",
                "Estado_Pago": "Al Día",
                "Dias_Atraso": "0",
                "Ultimo_Pago_Monto": " $ 450,000 ",
                "Requiere_Cobranza": "No",
            }
        ]

    monkeypatch.setattr(client, "read_sheet", fake_read_sheet)
    records = client.read_joined_records()
    assert len(records) == 1
    assert records[0].venta is not None
    assert records[0].mora is not None

