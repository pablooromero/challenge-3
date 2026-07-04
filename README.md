# Challenge 3

Agente de carga de formularios para Google Sheets + Google Forms.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Ejecutar

```bash
PYTHONPATH=. python3 scripts/run.py
```

## Tests

```bash
PYTHONPATH=. pytest tests
```

## Estado actual

- Lee `Ventas` y `Mora` desde el Sheet público vía `gviz/csv`.
- Normaliza moneda, tildes/case, centinela vacío y checkbox.
- Persiste estados `confirmed_prefill_browser`, `confirmed_http_fallback`, `unknown` y `quarantined`.
- Usa URLs prellenadas como camino principal de Playwright para evitar widgets custom inestables y mantener navegación/verificación visual.
- Tiene fallback resiliente a `formResponse` cuando el browser no logra confirmar la respuesta.
