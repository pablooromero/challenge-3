from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from app.models import NormalizedField
from app.prefill import build_prefilled_url


class FormFillError(RuntimeError):
    """Raised when a field cannot be filled or verified."""


class BaseGoogleFormDriver:
    def __init__(self, page: Page, timeout_ms: int) -> None:
        self.page = page
        self.timeout_ms = timeout_ms
        self.page.set_default_timeout(timeout_ms)

    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def goto_prefilled(self, payload) -> None:
        self.goto(build_prefilled_url(payload))

    def question_scope(self, label: str) -> Locator:
        return self.page.locator("div[role='listitem']").filter(
            has=self.page.get_by_text(label, exact=False)
        ).first

    def fill_text(self, label: str, value: str) -> None:
        locator = self.question_scope(label).locator("input[type='text']").first
        locator.fill(value)
        self.verify_text(locator, value)

    def verify_text(self, locator: Locator, expected: str) -> None:
        expect(locator).to_have_value(expected)
        actual = locator.input_value()
        if actual != expected:
            raise FormFillError(f"Textbox verification failed. Expected '{expected}', got '{actual}'")

    def verify_prefilled_field(self, field: NormalizedField) -> None:
        if field.field_type == "text":
            locator = self.question_scope(field.label).locator("input[type='text']").first
            self.verify_text(locator, str(field.value or ""))
            return
        if field.field_type == "radio":
            locator = self.page.get_by_role("radio", name=str(field.value), exact=True)
            self.verify_checked(locator, role="radio")
            return
        if field.field_type == "dropdown":
            selected = self.question_scope(field.label).locator(
                f"[role='option'][data-value='{field.value}'][aria-selected='true']"
            )
            expect(selected).to_have_count(1)
            return
        if field.field_type == "checkbox" and field.value:
            self.verify_checked(self.page.get_by_role("checkbox", name=field.options[0], exact=True), role="checkbox")

    def select_radio(self, option: str) -> None:
        locator = self.page.get_by_role("radio", name=option, exact=True)
        locator.click(force=True)
        self.verify_checked(locator, role="radio")

    def select_checkbox(self, option: str, enabled: bool) -> None:
        locator = self.page.get_by_role("checkbox", name=option, exact=True)
        if enabled and locator.get_attribute("aria-checked") != "true":
            locator.click()
        if enabled:
            self.verify_checked(locator, role="checkbox")

    def select_dropdown(self, label: str, option: str, options: list[str]) -> None:
        scope = self.question_scope(label)
        combo = scope.locator("[role='listbox']").first
        combo.click(force=True)
        steps = options.index(option) + 1
        for _ in range(steps):
            combo.press("ArrowDown")
        combo.press("Enter")
        expect(combo).to_contain_text(option)

    def verify_checked(self, locator: Locator, role: str) -> None:
        expect(locator).to_have_attribute("aria-checked", "true")
        actual = locator.get_attribute("aria-checked")
        if actual != "true":
            raise FormFillError(f"{role} verification failed; aria-checked={actual!r}")

    def fill_field(self, field: NormalizedField) -> None:
        if field.field_type == "text":
            self.fill_text(field.label, str(field.value or ""))
            return
        if field.field_type == "radio":
            self.select_radio(str(field.value))
            return
        if field.field_type == "dropdown":
            self.select_dropdown(field.label, str(field.value), field.options)
            return
        if field.field_type == "checkbox":
            if field.options:
                self.select_checkbox(field.options[0], bool(field.value))
            return
        raise FormFillError(f"Unsupported field type: {field.field_type}")

    def submit(self) -> None:
        self.page.get_by_role("button", name="Enviar", exact=True).click()

    def wait_for_confirmation(self) -> None:
        expect(self.page.get_by_text("Se registró tu respuesta")).to_be_visible()

    def capture(self, path: str) -> None:
        self.page.screenshot(path=path, full_page=True)
