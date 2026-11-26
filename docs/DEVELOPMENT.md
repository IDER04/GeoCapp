# Development guide

How to install, configure, run and test GeoCapital locally, and how the codebase is organized. The product overview and methodology live in the [README](../README.md); this document is for people who want to run or modify the code.

## Requirements

- Python 3.13 (the version used by the CI workflow in `.github/workflows/tests.yml`). A Dev Container definition is also provided in `.devcontainer/`.
- The runtime dependencies in `requirements.txt`: Streamlit, Plotly and pandas. The test suite uses the standard library only (`unittest` and `unittest.mock`), so there are no extra test dependencies.
- No database, paid service or bank connection is needed. The AI analyst is optional.

## Installation

```bash
git clone https://github.com/IDER04/GeoCapp.git
cd GeoCapp

python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the app

```bash
python -m streamlit run app.py
```

The app opens at <http://localhost:8501>. To run it without opening a browser or to change the port:

```bash
python -m streamlit run app.py --server.headless true --server.port 8599
```

Theme and server defaults are in `.streamlit/config.toml`.

## Run the tests

```bash
python -m unittest discover -s tests
```

The suite needs no network access, no API key and no `.env` file. Calls to the AI provider are mocked, which is also how the GitHub Actions workflow runs it.

## Configuration

The application runs fully without AI, using editorial content and deterministic calculations. To enable the optional AI analyst (an OpenAI-compatible API, OpenRouter by default), provide a key and, optionally, a model and base URL.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENROUTER_API_KEY` | For AI only | none | API key for the AI analyst |
| `LLM_MODEL` | No | `openai/gpt-4o` | Model identifier, for example `openrouter/free` for a free OpenRouter model. Takes precedence over `GEOCAPITAL_MODEL` |
| `LLM_BASE_URL` | No | `https://openrouter.ai/api/v1` | Base URL of the OpenAI-compatible API. HTTPS is required, except for localhost |
| `GEOCAPITAL_MODEL` | No | none | Legacy name for the model setting, still accepted |

Each setting is looked up in this order, highest priority first:

1. Process environment variables
2. A `.env` file in the project root
3. Streamlit secrets (`.streamlit/secrets.toml`)

**Local development with `.env`:**

```env
OPENROUTER_API_KEY="your-key"
LLM_MODEL="openai/gpt-4o"
```

**Local development with Streamlit secrets:** copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your key.

**Streamlit Community Cloud:** add the same keys in the app's *Secrets* settings.

Both `.env` and `.streamlit/secrets.toml` are listed in `.gitignore`. Never commit real keys. If the key is missing or a request fails, the analyst page falls back to a deterministic answer and shows a notice, with no crash.

## Project layout

```text
app.py                    Entry point: page config, navigation (8 routes), language selector
geocapital/
  scoring.py              Score, cost of equity (Ke), verdicts, portfolio metrics
  data.py                 JSON loading, formatting, comparisons, localization of display fields
  i18n.py                 FR/EN strings, t() helper, language state
  ai.py                   Optional OpenRouter client (config lookup, transport, fallback)
  analyst.py              Validated-facts payloads and prompt framing for the AI analyst
  limits.py               Per-session question limit for the analyst
  risk_lab.py             Sovereign Risk Lab calculations
  freshness.py            Data age and freshness indicators
  refresh.py              Review-first data refresh candidates (World Bank API)
  data_quality_audit.py   Data-quality audit generator
  ui.py                   Shared HTML/CSS components
  charts.py               Shared Plotly chart styling (presentation only)
views/                    One module per page
data/
  countries/*.json        One file per country
  events.json, meta.json  Decoder events; sources, parameters and scoring model
  i18n/en/*.json          English overlays for narrative content
  audit/, candidates/     Generated audit data and refresh candidates
assets/                   styles.css (visual theme) and logo
.devcontainer/            Dev Container definition
tests/                    unittest suite
docs/                     Methodology, model parameters and data-quality documents
```

## Design rules to respect

- **Calculations are deterministic.** Scores, verdicts and cost of equity are computed in `geocapital/scoring.py` from the data files. The AI layer never computes or invents numbers, dates or ratings; it only explains validated facts. Do not change scoring formulas without updating `docs/MODEL_PARAMS.md` and the tests.
- **Parameters live in data.** Model parameters and limits are read from `data/meta.json` rather than hard-coded.
- **Display text goes through `t()`.** All user-facing strings live in `geocapital/i18n.py` with both French and English entries; a test checks that the two languages have the same keys. Add both when you add a string. Internal identifiers, numbers and source data are never translated.
- **Narrative data is localized by overlay.** English text for country and event content lives in `data/i18n/en/`. Missing entries fall back to French.
- **Missing data is a signal.** Absent ratings or CDS spreads reduce solvency and block the "Invest" verdict instead of being filled in.

## Streamlit rendering notes

- Pages build HTML with `unsafe_allow_html=True`. Indented multi-line HTML can be parsed by Markdown as a code block. `ui.flatten_html()` and the normalizer installed at the start of `app.py` handle this for `st.markdown`; avoid sending HTML through other paths such as `st.write`.
- Widget values inside a rerun should not be changed programmatically. In `AppTest`-based tests, use a single run or pre-fill `st.session_state`.

## Data tooling

These commands read the production data and write reports only under `docs/` and `data/audit/`. They never modify `data/countries/` or `data/meta.json`.

```bash
# Regenerate the data-quality audit (data/audit/ and docs/DATA_QUALITY_AUDIT.md)
python -m geocapital.data_quality_audit
```

Data refresh candidates are produced by `geocapital/refresh.py` and reviewed manually before any data file is edited. See [`DATA_REFRESH_PLAN.md`](DATA_REFRESH_PLAN.md) for the policy.

## Further reading

- [`MODEL_PARAMS.md`](MODEL_PARAMS.md): meaning of every model parameter
- [`AI_LIMITS.md`](AI_LIMITS.md): analyst question limit
- [`SOVEREIGN_RISK_LAB.md`](SOVEREIGN_RISK_LAB.md): risk lab methodology and limits
- [`DATA_AUDIT.md`](DATA_AUDIT.md) and [`DATA_QUALITY_AUDIT.md`](DATA_QUALITY_AUDIT.md): data provenance and quality
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md): how to contribute
