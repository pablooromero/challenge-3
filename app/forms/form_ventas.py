from __future__ import annotations

from pathlib import Path

from app.forms.base import BaseGoogleFormDriver
from app.models import FormPayload


class VentasFormDriver(BaseGoogleFormDriver):
    def submit_payload(self, payload: FormPayload, evidence_dir: Path) -> None:
        self.goto_prefilled(payload)
        self.page.get_by_role("button", name="Siguiente", exact=True).click()
        current_page = min(field.page for field in payload.fields)
        max_page = max(field.page for field in payload.fields)

        while current_page <= max_page:
            for field in [item for item in payload.fields if item.page == current_page]:
                self.verify_prefilled_field(field)
            if current_page < max_page:
                self.page.get_by_role("button", name="Siguiente", exact=True).click()
            current_page += 1

        before_submit = evidence_dir / f"{payload.id_cliente}_ventas_before_submit.png"
        self.capture(str(before_submit))
        self.submit()
        self.wait_for_confirmation()
        confirmed = evidence_dir / f"{payload.id_cliente}_ventas_confirmed.png"
        self.capture(str(confirmed))
