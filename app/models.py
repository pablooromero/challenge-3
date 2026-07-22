from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FormName(str, Enum):
    VENTAS = "ventas"
    MORA = "mora"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED_BROWSER = "confirmed_browser"
    CONFIRMED_PREFILL_BROWSER = "confirmed_prefill_browser"
    CONFIRMED_HTTP_FALLBACK = "confirmed_http_fallback"
    UNKNOWN = "unknown"
    QUARANTINED = "quarantined"


class SheetRowBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    id_cliente: str = Field(alias="ID_Cliente")
    nombre_cliente: str = Field(alias="Nombre_Cliente")


class VentaRow(SheetRowBase):
    email: str = Field(alias="Email")
    telefono: str = Field(alias="Telefono")
    modelo_auto: str = Field(alias="Modelo_Auto")
    valor_vehiculo: str = Field(alias="Valor_Vehiculo")
    tipo_financiacion: str = Field(alias="Tipo_Financiacion")


class MoraRow(SheetRowBase):
    valor_vehiculo: str = Field(alias="Valor_Vehiculo")
    tipo_financiacion: str = Field(alias="Tipo_Financiacion")
    estado_pago: str = Field(alias="Estado_Pago")
    dias_atraso: str = Field(alias="Dias_Atraso")
    ultimo_pago_monto: str = Field(alias="Ultimo_Pago_Monto")
    requiere_cobranza: str = Field(alias="Requiere_Cobranza")


class ClientRecord(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id_cliente: str
    venta: VentaRow | None = None
    mora: MoraRow | None = None


class NormalizedField(BaseModel):
    field_key: str
    label: str
    field_type: Literal["text", "radio", "dropdown", "checkbox", "section"]
    required: bool = False
    page: int = 1
    value: str | bool | None = None
    options: list[str] = Field(default_factory=list)
    entry_id: str | None = None


class FormPayload(BaseModel):
    form_name: FormName
    id_cliente: str
    url: str
    title: str
    fields: list[NormalizedField]


class QuarantinedRecord(BaseModel):
    id_cliente: str
    form_name: FormName
    reason: str


class IngestResult(BaseModel):
    """Resultado de la ingesta: registros validos + filas que no parsearon."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    records: list[ClientRecord] = Field(default_factory=list)
    quarantined: list[QuarantinedRecord] = Field(default_factory=list)


class SubmissionRecord(BaseModel):
    id_cliente: str
    form_name: FormName
    status: SubmissionStatus
    reason: str | None = None

    @property
    def is_confirmed(self) -> bool:
        return self.status in {
            SubmissionStatus.CONFIRMED_BROWSER,
            SubmissionStatus.CONFIRMED_PREFILL_BROWSER,
            SubmissionStatus.CONFIRMED_HTTP_FALLBACK,
        }
