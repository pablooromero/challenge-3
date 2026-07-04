from __future__ import annotations

from openai import OpenAI


class LLMMappingError(RuntimeError):
    """Raised when the LLM cannot produce a valid mapping."""


class LLMValueReconciler:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def reconcile_option(self, raw_value: str, allowed_options: list[str]) -> str:
        prompt = (
            "Choose the closest valid option.\n"
            f"Raw value: {raw_value}\n"
            f"Allowed options: {allowed_options}\n"
            "Return only one option exactly as written."
        )
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        text = response.output_text.strip()
        if text not in allowed_options:
            raise LLMMappingError(f"LLM produced invalid option: {text!r}")
        return text

