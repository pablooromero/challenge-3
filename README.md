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
- Persiste estados `confirmed`, `unknown` y `quarantined`.
- Tiene drivers Playwright para ambos forms y smoke test preparado.
- Tiene fallback resiliente a `formResponse` cuando los widgets custom de Google Forms no responden bien a la automatización del browser.
