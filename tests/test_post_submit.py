from app.models import FormName, FormPayload, NormalizedField
from app.post_submit import build_form_response_payload
from app.prefill import build_prefilled_url


def test_build_form_response_payload_handles_checkbox_and_text() -> None:
    payload = FormPayload(
        form_name=FormName.MORA,
        id_cliente="FIAT-001",
        url="https://example.com",
        title="Control de Morosidad y Pagos",
        fields=[
            NormalizedField(
                field_key="id_cliente",
                label="ID de Cliente Asociado",
                field_type="text",
                value="FIAT-001",
                entry_id="1568255357",
            ),
            NormalizedField(
                field_key="requiere_cobranza",
                label="Requiere Acción de Cobranza Legal",
                field_type="checkbox",
                value=True,
                entry_id="76508310",
                options=["Sí, activar protocolo de cobranza legal"],
            ),
        ],
    )

    data = build_form_response_payload(payload, page_history="0")
    assert data["entry.1568255357"] == "FIAT-001"
    assert data["entry.76508310"] == "Sí, activar protocolo de cobranza legal"
    assert data["pageHistory"] == "0"


def test_build_prefilled_url_encodes_text_and_checkbox() -> None:
    payload = FormPayload(
        form_name=FormName.MORA,
        id_cliente="FIAT-002",
        url="https://docs.google.com/forms/d/e/test/viewform",
        title="Control de Morosidad y Pagos",
        fields=[
            NormalizedField(
                field_key="tipo_financiacion",
                label="Tipo Financiación",
                field_type="dropdown",
                value="Crédito Prendario",
                entry_id="191355245",
            ),
            NormalizedField(
                field_key="requiere_cobranza",
                label="Requiere Acción de Cobranza Legal",
                field_type="checkbox",
                value=True,
                entry_id="76508310",
                options=["Sí, activar protocolo de cobranza legal"],
            ),
        ],
    )

    url = build_prefilled_url(payload)
    assert "entry.191355245=Cr%C3%A9dito+Prendario" in url
    assert "entry.76508310=S%C3%AD%2C+activar+protocolo+de+cobranza+legal" in url
