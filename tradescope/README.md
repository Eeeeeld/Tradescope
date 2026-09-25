# TradeScope TW–ID

A Taiwan–Indonesia trade and currency dashboard built with **Streamlit, pandas and matplotlib**.
It works in English, Traditional Chinese (繁體中文) and Bahasa Indonesia, and converts **TWD → IDR** by default.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

On Windows you can double-click `run_windows.bat` instead. The app opens at http://localhost:8501.

## What's inside

| Page | Features |
|---|---|
| **Dashboard** | TWD/IDR, IDR/TWD, USD/TWD, USD/IDR cards · TWD→IDR chart · converter with swap and quick amounts · trade snapshot · latest news · rate alerts |
| **Currencies** | Chart & analysis (moving averages, % change, high/low, Holt trend forecast, rolling volatility, summary stats) · multi-currency comparison indexed to 100 · strength heatmap vs TWD · correlation matrix and rolling correlation · watchlist · historical conversion |
| **Taiwan–Indonesia trade** | Annual exports/imports and balance (2019–2024) · top HS chapters from UN Comtrade · HS code lookup · editable data table |
| **News feed** | Google News in 1–3 languages · topic filters (semiconductors, energy, nickel/EV, migrant workers, investment, policy) · headline search · sources and articles-per-day · CSV export |
| **Trade tools** | Landed-cost calculator (CIF, duty, VAT, PPh 22, fees, shown in TWD and IDR, per unit) · Incoterms 2020 reference |
| **Settings** | Language, default pair, default range, watchlist, rate alerts (saved to `data/settings.json`) |

Every chart has **PNG** and (where it makes sense) **CSV** download buttons.

## Data sources

- **Exchange rates:** [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api). It's free, needs no key, is updated daily and includes TWD and IDR. History goes back to March 2024.
- **Annual trade:** Taiwan Bureau of Foreign Trade (BOFT), Indonesia country file (Jan 2025), in `data/trade_tw_id_annual.csv`. Add new years in the app under *Trade → Edit data*.
- **Product detail:** UN Comtrade public preview API. It uses Indonesia's reported data, with Taiwan as partner code 490.
- **News:** Google News RSS search.

If there's no internet connection, the currency pages show a clearly labelled **sample** data set so the UI still works. News and Comtrade show a message instead; they never show made-up content.

## Project layout

```
app.py              UI and pages
core/i18n.py        all UI text in EN / 中文 / ID  (add strings here)
core/fx.py          exchange-rate fetching, caching, cross rates
core/trade.py       annual CSV + UN Comtrade
core/news.py        Google News RSS
core/analysis.py    moving averages, volatility, forecast, correlation, strength
core/charts.py      matplotlib style + chart helpers
core/costs.py       landed cost + Incoterms
core/settings.py    saved preferences
data/               trade CSV and settings.json
```

## Ideas for next steps

- Monthly trade data from Taiwan's customs portal (portal.sw.nat.gov.tw)
- Choropleth map of Taiwan's ASEAN trade
- Email/LINE notifications for rate alerts (scheduled job)
- Deploy free on Streamlit Community Cloud to share as a portfolio link
