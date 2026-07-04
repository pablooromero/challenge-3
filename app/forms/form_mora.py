from __future__ import annotations

from pathlib import Path

from app.forms.base import BaseGoogleFormDriver
from app.models import FormPayload


class MoraFormDriver(BaseGoogleFormDriver):
    def submit_payload(self, payload: FormPayload, evidence_dir: Path) -> None:
        self.goto_prefilled(payload)
        for field in payload.fields:
            self.verify_prefilled_field(field)

        before_submit = evidence_dir / f"{payload.id_cliente}_mora_before_submit.png"
        self.capture(str(before_submit))
        self.submit()
        self.wait_for_confirmation()
        confirmed = evidence_dir / f"{payload.id_cliente}_mora_confirmed.png"
        self.capture(str(confirmed))
