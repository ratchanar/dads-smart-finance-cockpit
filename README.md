# Dad's Smart Finance Cockpit

A modular Streamlit demo for an Indian retail investor. It includes a market
digest, portfolio auditor, IPO tracker, valuation watchlist and quiet-alert
preferences.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## Optional Hugging Face summarisation

The application runs immediately without downloading a language model. To
enable BART summarisation, install a compatible PyTorch and Transformers build,
then change `DadFinanceAnalytics(use_transformers=False)` in `app.py` to
`use_transformers=True`. The first run may download model weights and require
substantial disk space and memory. If loading or inference fails, the app
automatically uses its local extractive summariser.

## Portfolio CSV format

Required columns:

```csv
symbol,asset_type,quantity,avg_cost,current_price
RELIANCE,Equity,10,2450,2910
HDFCBANK,Equity,20,1510,1685
NIFTY50MF,Mutual Fund,100,185,224
```

`name` is optional. Common aliases such as `ticker`, `qty`, `units`,
`average_cost`, `buy_price`, `ltp` and `price` are accepted.

## Architecture

- `app.py`: Streamlit layout and user interactions.
- `analytics.py`: digest summarisation, portfolio diversification score and
  volatility-floor checks.
- `data.py`: deterministic mock data, portfolio CSV validation and synthetic
  price history.
- `notifications.py`: quiet notification logger with safe provider integration
  points.

## Important limitations

- Every displayed index value, headline, IPO, valuation discount and synthetic
  price series is mock data. There is no NSE/BSE feed or real-time news source.
- The IPO buckets are deliberately illustrative. They are not forecasts,
  ratings or recommendations.
- The portfolio score is a heuristic for concentration and asset mix. It does
  not calculate a genuine historical covariance matrix or account for goals,
  liabilities, tax, liquidity needs or risk tolerance.
- The volatility floor is an educational example, not a validated trading
  stop. It uses synthetic prices in this demo. A live implementation should
  use corporate-action-adjusted market data and carefully tested methodology.
- Notifications are logged only. No WhatsApp, SMTP or other external message
  is sent. A production integration needs explicit consent, secrets management,
  rate limiting, retries, audit logs and provider compliance.
- Do not upload credentials, account numbers or other sensitive information.
  Uploaded CSV data remains in the Streamlit session in this demo.
