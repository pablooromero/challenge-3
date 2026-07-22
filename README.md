# Challenge 3 - Agente de carga de formularios

Agente para leer datos desde un Google Sheets con dos pestañas (`Ventas` y `Mora`) y completar dos Google Forms asociados, manteniendo navegación browser, validación previa al envío, evidencia de ejecución e idempotencia.

## Enfoque

La solución usa un core determinístico y auditable. El flujo principal no intenta pelear con los widgets custom de Google Forms mediante clicks frágiles; genera URLs prellenadas con los `entry.*` reales del formulario, abre esas URLs con Playwright, verifica que los valores estén cargados, navega las secciones y envía desde el browser.

Si el browser no logra confirmar el envío, existe un fallback transaccional a `formResponse`, pero en la última corrida validada no fue necesario usarlo.

Resultado de la última corrida real:

```text
Run summary:
- confirmed_prefill_browser: 8
- confirmed_http_fallback: 0
- unknown: 0
- quarantined: 0
```

## Arquitectura

```text
Google Sheets
  -> app/sheets.py          lee Ventas y Mora via gviz/csv
  -> app/models.py          modelos Pydantic y estados de envio
  -> app/normalize.py       normalizacion y payloads por formulario
  -> config/mapping.yaml    labels, opciones, entry_id, form_id y page_history
  -> app/prefill.py         genera URLs prellenadas
  -> app/forms/*            navegacion/verificacion/envio con Playwright
  -> app/orchestrator.py    retries, idempotencia, fallback y estado
  -> app/report.py          resumen final
```

## Flujo end to end

1. Lee las pestañas `Ventas` y `Mora` del Sheet publico.
2. Hace join por `ID_Cliente`.
3. Normaliza datos antes de tocar el navegador:
   - moneda: `" $ 18,500,000 "` -> `"18500000"`
   - centinela de pago vacío: `" $ - "` -> `"0"`
   - opciones case/tilde-insensitive: `"Al Día"` -> `"Al día"`
   - checkbox: `"Sí"` / `"No"` -> boolean
4. Construye un `FormPayload` por cliente y formulario.
5. Genera una URL prellenada con `entry.*`.
6. Playwright abre el formulario, verifica campos, navega secciones y envía.
7. Detecta confirmación post-submit.
8. Persiste el estado por `(ID_Cliente, form)`.
9. Genera screenshots y videos en `evidence/`.

## Estados

- `confirmed_prefill_browser`: el envio fue confirmado desde Playwright usando URL prellenada.
- `confirmed_http_fallback`: el browser fallo y el envio fue confirmado por `formResponse`.
- `unknown`: pudo haber ocurrido un envio, pero no se pudo confirmar; no se reintenta automaticamente.
- `quarantined`: el registro no se envio por validacion, datos invalidos o error no recuperable.

## Setup

```bash
cd challenge-3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
cp .env.example .env
```

## Variables de entorno

| Variable | Uso |
|---|---|
| `SHEET_ID` | ID del Google Sheets fuente. |
| `HEADLESS` | `true` para correr sin UI, `false` para demo visual. |
| `SHEETS_VERIFY_SSL` | Verificacion SSL para requests HTTP. |
| `PLAYWRIGHT_TIMEOUT_MS` | Timeout default de Playwright. |
| `EVIDENCE_DIR` | Carpeta de screenshots/videos. |
| `STATE_FILE` | Archivo de idempotencia. |
| `ALLOW_FORM_POST_FALLBACK` | Habilita fallback a `formResponse`. |
| `ENABLE_LLM` | Reservado para capa IA opcional. |
| `OPENAI_API_KEY` | API key para capa IA opcional. |
| `OPENAI_MODEL` | Modelo para capa IA opcional. |

## Ejecucion

Modo headless:

```bash
HEADLESS=true PYTHONPATH=. python3 scripts/run.py
```

Modo demo visual:

```bash
HEADLESS=false PYTHONPATH=. python3 scripts/run.py
```

Para repetir una corrida completa desde cero, borrar el estado local:

```bash
rm -f state/submissions.json
HEADLESS=true PYTHONPATH=. python3 scripts/run.py
```

## Tests

```bash
PYTHONPATH=. python3 -m pytest tests -q
```

El smoke E2E real esta opt-in porque envia respuestas a Google Forms:

```bash
RUN_SMOKE_E2E=1 HEADLESS=true PYTHONPATH=. python3 -m pytest tests/test_smoke_e2e.py -q
```

## Evidencia

La corrida deja artefactos en `evidence/`:

- `*_before_submit.png`: estado del formulario antes de enviar.
- `*_confirmed.png`: pantalla de confirmacion.
- `videos/*.webm`: video de Playwright por contexto.

Ejemplos utiles para revisar:

- `evidence/FIAT-001_mora_before_submit.png`
- `evidence/FIAT-001_ventas_before_submit.png`
- `evidence/FIAT-002_mora_before_submit.png`

## Seguridad y datos

- No hay secretos commiteados.
- `state/submissions.json` y `evidence/` estan gitignored porque contienen datos de ejecucion y PII.
- `config/mapping.yaml` si se commitea: no contiene secretos y es parte del contrato funcional Sheet -> Forms.
- PII (emails, telefonos, montos) se enmascara en los `reason` persistidos en el estado y en el reporte via `app/masking.py`, incluso cuando provienen de una URL prellenada embebida en un mensaje de error.

## Nota tecnica

Google Forms usa controles custom para dropdowns, radios y checkboxes. La estrategia de URLs prellenadas evita depender de clicks inestables sobre esos widgets, pero mantiene la navegacion y verificacion browser. El fallback `formResponse` queda como mecanismo de resiliencia auditado, no como camino principal.
