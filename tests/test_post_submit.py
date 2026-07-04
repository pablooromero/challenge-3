from app.models import FormName, FormPayload, NormalizedField
from app.post_submit import build_form_response_payload


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

