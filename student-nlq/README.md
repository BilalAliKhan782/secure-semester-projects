# Student NLQ

A Flask interface that maps supported natural-language questions to parameterized Oracle SQL/PLSQL and MongoDB queries.

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Load the .env values into your shell, then:
python app.py
```

Run the scripts under `oracle/` in numeric order. The server listens only on `127.0.0.1:5000` by default. Set `FLASK_DEBUG=1` only during local development; debug plans and internal errors are hidden by default.
