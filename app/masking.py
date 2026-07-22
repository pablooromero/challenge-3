from __future__ import annotations

import re

# Emails y secuencias numericas largas (telefonos, montos, entry ids) son los
# vectores de PII/dato sensible que pueden colarse en reasons o en URLs
# prellenadas embebidas en mensajes de error.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_NUMBER_RE = re.compile(r"\b\d{7,}\b")


def mask_pii(text: str | None) -> str | None:
    """Redacta PII de un texto libre antes de persistirlo o mostrarlo.

    Mantiene identificadores no sensibles como `FIAT-001` (tienen letras/guion)
    y solo enmascara emails y numeros largos (telefonos, montos, entry ids).
    """
    if text is None:
        return None
    masked = _EMAIL_RE.sub("[email]", text)
    masked = _LONG_NUMBER_RE.sub("[num]", masked)
    return masked
