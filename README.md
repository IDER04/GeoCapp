# GeoCapp — Know the past to anticipate the future

An educational Streamlit application that connects **a country's history**, **its financial indicators** and **a readable investment decision**: a score out of 100, a required return (Ke, Damodaran method) and a four-level verdict.

> Educational prototype. The data is curated, dated and sourced. The application places no orders and does not constitute investment advice.

## User journey

1. **Living map** — choropleth map of the 10 countries, with attractiveness / risk / growth / currency filters and three investor profiles.
2. **Country profile** — historical timeline, institutions, relationships (allies, rivals, dependencies), strengths, risks and opportunities.
3. **Dashboard** — 11 indicators with green / orange / red status, source, reference year and a plain-language explanation.
4. **Score & verdict** — transparent breakdown into 5 components, Ke, verdict and three reasons.
5. **News decoder** — causal chain from event to economy to finance to winners and losers, with a historical parallel.
6. **AI analyst** — ask your questions in French or English; the answer follows the language of your question and relies only on the validated facts in the database.
7. **Global portfolio** — a fictional €100,000, weighted required return, volatility, diversification and diagnosis.
8. **Progress** — mind map, quick quiz and badges.
9. **Sources & method** — formulas, weightings, limitations and disclaimers.

## The 10 MVP countries

United States, France, Japan, China, Saudi Arabia, United Arab Emirates, Morocco, South Africa, Lebanon, Syria.

## Run locally

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

The application opens at <http://localhost:8501>.

For detailed installation, configuration, testing and code organization, see [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md). To contribute, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Data and methodology

- One JSON file per country in `data/countries/`, complemented by `data/meta.json` and `data/events.json`.
- **GeoCapp score**: five components (dynamism, macro stability, solvency, institutions, openness & business climate), each rated from 0 to 100 and weighted according to the Prudent / Balanced / Bold profile.
- **Required return**: `Ke = 4.20% + 1.0 × 4.50% + country risk premium`.
- **Country risk premium**: the maximum of the rating spread and the CDS spread, multiplied by 1.5 (Damodaran's equity/bond volatility ratio).
- **Missing data**: a missing rating or an unquoted CDS lowers the solvency component and **blocks the "Invest" verdict**. For Lebanon and Syria, the absence of data is treated as a risk signal.
- Qualitative scores (governance, resilience, business climate, openness, currency stability) are explicit GeoCapp assessments, not raw data.

## Artificial intelligence (optional)

The application works **entirely without AI**, thanks to editorial content and deterministic calculations.

To enable AI (OpenRouter, default model `openai/gpt-4o`):

1. Create a `.env` file at the project root (never committed; excluded by `.gitignore`):

```env
OPENROUTER_API_KEY = "your_key"
GEOCAPITAL_MODEL = "openai/gpt-4o"
```

2. Or, on Streamlit Community Cloud, add the key to the app's *secrets*:

```toml
OPENROUTER_API_KEY = "your_key"
GEOCAPITAL_MODEL = "openai/gpt-4o"
```

## AI analyst (OpenRouter)

The "Analyst" page offers a bilingual conversational interface: the answer follows the language of the question (French or English), regardless of the interface display language. It combines:

1. **Local retrieval**: country profiles, comparator, verdicts, cost of capital (Damodaran), decoder events and portfolio. Calculations remain deterministic (Python); the model computes nothing.
2. **Strict framing**: each question sends only a set of validated facts (with sources and dates) for the selected intent; missing data is listed as "data not available".
3. **Three visible registers**: ● Validated facts, ◆ AI interpretation, ○ Hypothesis. The model must qualify its sentences ("Interpretation: …", "Hypothesis: …").
4. **Local memory**: the conversation lives in Streamlit's `session_state` (no persistence, no leakage between sessions); the "Clear conversation" button resets it, and only the last 6 exchanges are sent back to the API.
5. **Fallback without API**: without a key, or if OpenRouter fails, the page displays the same factual context and the deterministic analysis (in the language of the question) with an explicit notice.

The AI receives only facts already validated in the database. It explains, rephrases and connects; it creates no figure, no date and no rating.

## Structure

```
app.py                     # entry point, navigation, session_state
geocapital/
  scoring.py               # score, Ke, verdicts, portfolio metrics
  data.py                  # JSON loading, formatting, comparisons
  i18n.py                  # centralized FR/EN labels, t(), language store
  ai.py                    # optional AI layer via OpenRouter
  analyst.py               # validated facts and framing for the AI analyst
  ui.py                    # HTML/CSS components
views/                     # 8 pages, including the Analyst
data/
  countries/*.json         # 10 country profiles
  meta.json                # sources, parameters, methodology
  events.json              # 10 decoder events
assets/styles.css          # dark theme and components
.streamlit/config.toml     # Streamlit theme
```

## Deployment

1. Push the repository to GitHub.
2. On [Streamlit Community Cloud](https://share.streamlit.io), create an app with `app.py` as the main file.
3. Optionally add `OPENROUTER_API_KEY` to the secrets.
4. No database, paid service or bank connection is required.

## Limitations

- Reference data covers 2024–2025 and is not updated in real time.
- Simplified portfolio model: correlations by country group, educational volatility, no currency hedging.
- The score does not replace due diligence, a valuation analysis or personalized advice.
