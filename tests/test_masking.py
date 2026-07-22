"""Tests del enmascarado de PII en reasons/logs (fix PII)."""
from app.masking import mask_pii


def test_masks_email() -> None:
    masked = mask_pii("error para carlos.m@mail.com")
    assert "carlos.m@mail.com" not in masked
    assert "[email]" in masked


def test_masks_phone_and_amounts() -> None:
    masked = mask_pii("telefono 54119876543 monto 18500000")
    assert "54119876543" not in masked
    assert "18500000" not in masked
    assert "[num]" in masked


def test_masks_pii_inside_prefilled_url() -> None:
    url = "goto failed: .../viewform?entry.1855970967=carlos.m@mail.com&entry.136415275=54119876543"
    masked = mask_pii(url)
    assert "carlos.m@mail.com" not in masked
    assert "54119876543" not in masked


def test_keeps_non_pii_identifiers() -> None:
    masked = mask_pii("quarantined FIAT-001 / mora: parse_error")
    assert "FIAT-001" in masked
    assert "parse_error" in masked


def test_none_passthrough() -> None:
    assert mask_pii(None) is None
