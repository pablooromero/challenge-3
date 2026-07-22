from __future__ import annotations

from pathlib import Path

from app.forms.base import BaseGoogleFormDriver
from app.models import FormPayload


class MoraFormDriver(BaseGoogleFormDriver):
    def prepare(self, payload: FormPayload, evidence_dir: Path) -> None:
        """Fase idempotente: abre y verifica cada campo. No envia nada."""
        self.goto_prefilled(payload)
        for field in payload.fields:
            self.verify_prefilled_field(field)

        before_submit = Path(evidence_dir) / f"{payload.id_cliente}_mora_before_submit.png"
        self.capture(str(before_submit))

    def submit_and_confirm(self, payload: FormPayload, evidence_dir: Path) -> None:
        """Fase de envio: ocurre una unica vez, nunca se reintenta a ciegas."""
        self.submit()
        self.wait_for_confirmation()
        confirmed = Path(evidence_dir) / f"{payload.id_cliente}_mora_confirmed.png"
        self.capture(str(confirmed))
