

│── config
    ├── keywords.yaml
│── data
    ├──db.sqlite3
│n8n
    ├── workflow_trend_extraction.json
│── src/
│ ├── server.py # FastAPI app (API endpoints)
│ ├── pipeline.py
│ ├──config.py
│ ├──__init__.py
│── reports/ # Generated reports will be saved here
    ├──assets
	├── category_counts.png
	├── category_sentiment.png
	├── style.css
   ├── templates
	├── weekly_report.html
	├── weekly_report_2025-08-23.html
	├── weekly_report_2025-08-23.pdf
├── samples
   ├── make_sample_data.py
│── requirements.txt # Python dependencies
│── README.md # Project documentation
├── run_pipeline.py


---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd trend_extractor

### 2. Create and activate a virtual environment

python3 -m venv .venv
source .venv/bin/activate   # Mac/Linux
.venv\Scripts\activate      # Windows

### 3. Install dependencies

pip install -r requirements.txt

### 4. Run the API Server

uvicorn src.server:app --reload --port 8000

The API will be available at:
👉 http://127.0.0.1:8000
Swagger UI (API docs):
👉 http://127.0.0.1:8000/docs

### 5. API Endpoints

| Method | Endpoint  | Description                                           |
| ------ | --------- | ----------------------------------------------------- |
| `GET`  | `/`       | Health check (API running)                            |
| `GET`  | `/health` | Returns status `"ok"`                                 |
| `POST` | `/ingest` | Ingests new trends (mock/sample data if no API keys)  |
| `GET`  | `/trends` | Returns recent trends (JSON list of marketing trends) |
| `POST` | `/report` | Generates an HTML (or PDF) weekly report              |

### 5. Example usage

1. Ingest Trends
POST /ingest
{
  "days": 7
}

2. View Trends
GET /trends?limit=10

Returns 10 recent trends in JSON format:
[
  {
    "platform": "Twitter",
    "title": "AI in Marketing",
    "category": "Tech",
    "engagement": 452,
    "sentiment_compound": 0.65,
    "created_at": "2025-08-23",
    "url": "http://example.com/trend"
  }
]

3. Generate Report
POST /report
{
  "days": 7,
  "format": "html"
}

Output:
{"report": "reports/weekly_report.html"}

📈 Features
Collects & stores trends (mock data or real APIs).
Performs sentiment analysis on trend text.
Calculates engagement metrics.
Generates beautiful HTML & PDF reports.
Simple REST API with Swagger UI.

🛠️ Tech Stack
Python 3.9+
FastAPI (backend framework)
SQLite (lightweight DB)
Pandas (data analysis)
Jinja2 (HTML templating)
FPDF (PDF reports)

Notes
If no API keys are configured, ingestion runs in mock mode and generates sample data for testing.
Reports are stored in the reports/ folder.
Designed to be extendable for real data sources like Twitter API, Reddit API, or Google Trends.
