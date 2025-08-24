
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import datetime
import os


try:
    from src.pipeline import ingest_and_store, generate_report, query_last_days
except ImportError:
    ingest_and_store = None
    generate_report = None
    query_last_days = None

app = FastAPI(title="Trend Extraction API")

class IngestBody(BaseModel):
    days: int = 7

class ReportBody(BaseModel):
    days: int = 7
    format: str = "html"


@app.get("/")
def root():
    return {"message": "🚀 Trend Extractor API is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/mock")
def mock_data():
    return {
        "trends": [
            {"topic": "AI in Marketing", "engagement": 1500, "sentiment": "positive"},
            {"topic": "TikTok Ads", "engagement": 1200, "sentiment": "neutral"},
            {"topic": "SEO automation", "engagement": 900, "sentiment": "positive"},
        ],
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.post("/ingest")
def ingest(body: IngestBody):
    if ingest_and_store is None:
        return {"message": "⚠️ Mock mode: ingestion not implemented"}
    try:
        inserted = ingest_and_store(days=body.days)
        return {"inserted": inserted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


@app.post("/report")
def report(body: ReportBody):
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)

    
    df = query_last_days(body.days)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No trends available to generate report.")

    cols = ['platform','title','category','engagement','sentiment_compound','created_at','url']
    trends = df[cols].head(20).to_dict(orient='records')

    if body.format.lower() == "html":
        file_path = os.path.join(report_dir, f"weekly_report_{datetime.date.today()}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("<h1>📊 Weekly Marketing Trends Report</h1>")
            f.write(f"<p>Period: Last {body.days} days</p>")
            f.write("<ul>")
            for t in trends:
                f.write(f"<li><b>{t['title']}</b> ({t['platform']}, {t['category']}) - "
                        f"Engagement: {t['engagement']}, Sentiment: {t['sentiment_compound']:.2f}, "
                        f"<a href='{t['url']}'>Link</a></li>")
            f.write("</ul>")
        return FileResponse(file_path, media_type="text/html")

    elif body.format.lower() == "pdf":
        file_path = os.path.join(report_dir, f"weekly_report_{datetime.date.today()}.pdf")
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 16)
        c.drawString(150, height - 50, "📊 Weekly Marketing Trends Report")

        c.setFont("Helvetica", 10)
        c.drawString(50, height - 70, f"Period: Last {body.days} days")

        y = height - 100
        for i, t in enumerate(trends, start=1):
            text = f"{i}. {t['title']} ({t['platform']}, {t['category']}) | Engagement: {t['engagement']} | Sentiment: {t['sentiment_compound']:.2f}"
            c.drawString(50, y, text[:110])  
            y -= 20
            if y < 50:  
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50

        c.showPage()
        c.save()
        return FileResponse(file_path, media_type="application/pdf")

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'html' or 'pdf'.")

@app.get("/trends")
def trends(limit: int = 20):
    if query_last_days is None:
        
        return [
            {"platform": "Reddit", "title": "AI in Marketing", "category": "content marketing", "engagement": 1500, "sentiment_compound": 0.9, "created_at": str(datetime.date.today()), "url": "http://example.com"},
            {"platform": "X", "title": "TikTok Ads", "category": "social media marketing", "engagement": 1200, "sentiment_compound": 0.2, "created_at": str(datetime.date.today()), "url": "http://example.com"},
        ][:limit]

    df = query_last_days(30)
    if df is None or df.empty:
        return []
    cols = ['platform', 'title', 'category', 'engagement', 'sentiment_compound', 'created_at', 'url']
    return df[cols].head(limit).to_dict(orient='records')
