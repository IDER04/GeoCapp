# Contributing to GeoCapital

Thanks for your interest in GeoCapital. This is an educational project, and suggestions, bug reports and pull requests are welcome.

## Before you start

- Set up your environment and run the tests with the steps in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).
- For anything beyond a small fix, open an issue first so we can agree on the approach.
- GeoCapital is a teaching tool. It places no orders and is not investment advice, and contributions should keep that framing.

## Reporting issues

Please include:

- What you expected and what happened
- Steps to reproduce, and the page and language (FR/EN) involved
- Your Python and Streamlit versions

For data errors, include the country, indicator, the value shown, and a source for the correct value.

Do not paste API keys, `.env` contents or other secrets into issues. If you believe you have found a security problem, please open an issue that describes it without including any secret, or contact the maintainer privately through the details on the [GitHub profile](https://github.com/IDER04).

## Making a change

1. Fork the repository and create a branch from `main` (for example `fix/ke-rounding` or `feat/new-indicator`).
2. Keep the change focused: one topic per pull request.
3. Run the full test suite and make sure it passes:

   ```bash
   python -m unittest discover -s tests
   ```

4. Open a pull request against `main` and describe what changed and why. The GitHub Actions workflow runs the same test suite on every pull request.

## Guidelines

**Code**
- Follow the existing structure and naming. Keep calculations in `geocapital/scoring.py` and display code in `views/` and `geocapital/ui.py`.
- Add or update tests for any behavior you change.
- Do not add new dependencies or external services without discussing them first.

**Financial logic**
- Scores, verdicts and cost of equity are deterministic. If you change a formula or weight, update `docs/MODEL_PARAMS.md` and the tests in the same pull request, and explain the reasoning.
- The AI analyst must stay grounded: it explains validated facts and never produces its own numbers, dates or ratings.

**Data**
- Every figure needs a source and a reference year. Keep the real reference year; do not relabel older data as current.
- Do not edit files in `data/countries/` directly from automated refresh output. Review candidates first, following [`docs/DATA_REFRESH_PLAN.md`](docs/DATA_REFRESH_PLAN.md).
- Qualitative scores are explicit editorial assessments and should be documented as such.

**Languages**
- The interface is bilingual (French and English). Add every user-facing string to `geocapital/i18n.py` in both languages. Never translate identifiers, numbers or source data.

**Secrets and local files**
- Never commit `.env`, `.streamlit/secrets.toml`, API keys or local paths. They are ignored by `.gitignore`; check `git status` before committing.

## Commit messages

Write short, descriptive messages in the imperative mood, for example `Fix portfolio volatility rounding` or `Add Brazil English overlay`.
