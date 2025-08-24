
import os
from src.pipeline import init_db, ingest_and_store, generate_report

def main():
    # Use MOCK mode if not set
    os.environ.setdefault("MOCK_MODE", "true")
    print("MOCK_MODE =", os.environ.get("MOCK_MODE"))

    print("Initializing DB...")
    init_db()

    print("Ingesting (this may use mock data) ...")
    n = ingest_and_store(days=7)
    print(f"Inserted/updated {n} records into the DB.")

    print("Generating weekly report (HTML)...")
    report_path = generate_report(days=7, out_html="reports/weekly_report.html", make_pdf=False)
    print("Report saved to:", report_path)

if __name__ == "__main__":
    main()
