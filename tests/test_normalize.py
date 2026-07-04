from pathlib import Path

from app.models import ClientRecord, FormName, MoraRow
from app.normalize import (
    build_form_payload,
    load_mapping,
    match_option,
    normalize_checkbox,
    normalize_currency,
)


def test_normalize_currency_handles_symbols_and_sentinel() -> None:
    assert normalize_currency(" $ 18,500,000 ") == "18500000"
    assert normalize_currency(" $ -   ") == "0"


def test_match_option_is_case_and_accent_insensitive() -> None:
    options = ["Al día", "Moroso"]
    assert match_option("Al Día", options) == "Al día"


def test_checkbox_maps_yes_no() -> None:
    assert normalize_checkbox("Sí") is True
    assert normalize_checkbox("No") is False


def test_build_form_payload_normalizes_mora_fields() -> None:
    mapping = load_mapping(Path(__file__).resolve().parents[1] / "config" / "mapping.yaml")
    mora = MoraRow.model_validate(
        {
            "ID_Cliente": "FIAT-002",
            "Nombre_Cliente": "Ana María Silva",
            "Valor_Vehiculo": " $ 22,100,000 ",
            "Tipo_Financiacion": "Plan de Ahorro",
            "Estado_Pago": "Al Día",
            "Dias_Atraso": "45",
            "Ultimo_Pago_Monto": " $ -   ",
            "Requiere_Cobranza": "Sí",
        }
    )
    payload = build_form_payload(FormName.MORA, "FIAT-002", mora, mapping)
    values = {field.field_key: field.value for field in payload.fields}
    assert values["valor_vehiculo"] == "22100000"
    assert values["estado_pago"] == "Al día"
    assert values["ultimo_pago_monto"] == "0"
    assert values["requiere_cobranza"] is True
