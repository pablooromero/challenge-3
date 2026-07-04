from __future__ import annotations

import json
from pathlib import Path

from app.models import FormName, SubmissionRecord, SubmissionStatus


class SubmissionStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, SubmissionRecord]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return {key: SubmissionRecord.model_validate(value) for key, value in data.items()}

    def save(self, state: dict[str, SubmissionRecord]) -> None:
        serialized = {
            key: value.model_dump(mode="json")
            for key, value in state.items()
        }
        self.path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    @staticmethod
    def make_key(id_cliente: str, form_name: FormName) -> str:
        return f"{id_cliente}:{form_name.value}"

    def upsert(
        self,
        state: dict[str, SubmissionRecord],
        id_cliente: str,
        form_name: FormName,
        status: SubmissionStatus,
        reason: str | None = None,
    ) -> dict[str, SubmissionRecord]:
        key = self.make_key(id_cliente, form_name)
        state[key] = SubmissionRecord(
            id_cliente=id_cliente,
            form_name=form_name,
            status=status,
            reason=reason,
        )
        self.save(state)
        return state

