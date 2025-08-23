"""
Single-file pipeline for extraction -> filter -> sentiment -> category -> store -> report
Designed so beginners can copy/paste and run in MOCK_MODE.
"""
import os, json, sqlite3, hashlib, datetime
from typing import List, Dict, Any
# from .config import DB_PATH, load_keywords, MOCK_MODE, GEO, REPORTS_DIR
from src.config import DB_PATH, load_keywords, MOCK_MODE, GEO, REPORTS_DIR
import pandas as pd
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- helpers ------------------------------------------------
def _ensure_dirs():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(os.path.join(REPORTS_DIR, "assets"), exist_ok=True)
    os.makedirs(os.path.join(REPORTS_DIR, "templates"), exist_ok=True)

# --- connectors (lightweight; only used when MOCK_MODE=False) ---
def fetch_x_recent(keywords: List[str], days: int = 7, max_results: int = 100) -> List[Dict[str, Any]]:
    """Fetch X (Twitter) posts — returns [] when credentials/libraries are missing"""
    try:
        import tweepy
    except Exception:
        return []

    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        return []

    client = tweepy.Client(bearer_token=token, wait_on_rate_limit=True)
    q = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
    query = f"({q}) -is:retweet lang:en"
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=days)
    tweets = []
    try:
        paginator = tweepy.Paginator(
            client.search_recent_tweets,
            query=query,
            start_time=start.isoformat("T")+"Z",
            end_time=end.isoformat("T")+"Z",
            max_results=100,
            tweet_fields=["created_at","public_metrics","lang","text"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        users = {}
        for page in paginator:
            if page.includes and 'users' in page.includes:
                for u in page.includes['users']:
                    users[u.id] = u
            if page.data:
                for t in page.data:
                    author = users.get(t.author_id).username if t.author_id in users else None
                    metrics = t.public_metrics or {}
                    tweets.append({
                        "id": str(t.id),
                        "platform": "x",
                        "created_at": t.created_at.isoformat() if hasattr(t, "created_at") else None,
                        "title": t.text[:120],
                        "text": t.text,
                        "author": author,
                        "url": f"https://x.com/{author}/status/{t.id}" if author else None,
                        "lang": t.lang,
                        "engagement": int(metrics.get("like_count",0)) + int(metrics.get("retweet_count",0)) + int(metrics.get("reply_count",0)),
                        "raw_metrics": metrics,
                    })
    except Exception:
        pass
    return tweets

def fetch_reddit(keywords: List[str], days: int = 7, limit: int = 200) -> List[Dict[str, Any]]:
    try:
        import praw
    except Exception:
        return []

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    if not (client_id and client_secret and user_agent):
        return []

    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    subs = ["marketing","SEO","socialmedia","advertising","content_marketing","PPC","bigseo"]
    items = []
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    q = " OR ".join([f'"{k}"' if " " in k else k for k in keywords]) if keywords else None
    try:
        for sr in subs:
            for s in reddit.subreddit(sr).search(q, sort="new", time_filter="week", limit=limit):
                created = datetime.datetime.utcfromtimestamp(s.created_utc)
                if created < since:
                    continue
                text = (s.title or "") + " " + (s.selftext or "")
                items.append({
                    "id": s.id,
                    "platform": "reddit",
                    "created_at": created.isoformat(),
                    "title": s.title or "",
                    "text": text,
                    "author": str(s.author) if s.author else None,
                    "url": f"https://www.reddit.com{s.permalink}",
                    "lang": "en",
                    "engagement": int(s.score or 0) + int(s.num_comments or 0),
                    "raw_metrics": {"score": int(s.score or 0), "num_comments": int(s.num_comments or 0)}
                })
    except Exception:
        pass
    return items

def fetch_google_trends(keywords: List[str], top_n: int = 20, pytrends=None) -> List[Dict[str, Any]]:
    try:
        from pytrends.request import TrendReq
    except Exception:
        return []

    py = TrendReq(hl="en-US", tz=330)
    results = []
    try:
        daily = py.trending_searches(pn=GEO if len(GEO)==2 else "india")
        if not daily.empty:
            for i, row in daily.head(top_n).iterrows():
                term = row[0]
                results.append({
                    "id": f"gtrends-daily-{term}",
                    "platform": "gtrends",
                    "created_at": None,
                    "title": term,
                    "text": term,
                    "author": None,
                    "url": f"https://trends.google.com/trends/explore?q={term}",
                    "lang": "en",
                    "engagement": 0,
                    "raw_metrics": {"type": "daily_trending"},
                })
        # interest over time for first few keywords
        seed = keywords[:5] if keywords else ["marketing"]
        py.build_payload(seed, timeframe="now 7-d", geo=GEO if len(GEO)==2 else "")
        iot = py.interest_over_time()
        if iot is not None and not iot.empty:
            for col in iot.columns:
                if col == 'isPartial':
                    continue
                results.append({
                    "id": f"gtrends-iot-{col}",
                    "platform": "gtrends",
                    "created_at": None,
                    "title": col,
                    "text": col,
                    "author": None,
                    "url": f"https://trends.google.com/trends/explore?q={col}",
                    "lang": "en",
                    "engagement": int(iot[col].iloc[-1]),
                    "raw_metrics": {"type": "interest_over_time", "latest": int(iot[col].iloc[-1])},
                })
    except Exception:
        pass
    return results

# --- extract / transform / classify / sentiment --------------------
def extract_all(keywords: List[str], days:int=7) -> List[Dict[str,Any]]:
    out = []
    out.extend(fetch_x_recent(keywords, days=days))
    out.extend(fetch_reddit(keywords, days=days))
    out.extend(fetch_google_trends(keywords))
    return out

def build_keyword_list() -> List[str]:
    keys = load_keywords()
    flat = []
    for v in keys.get("categories", {}).values():
        flat.extend(v)
    return list(set(flat))

def normalize_record(r: Dict[str, Any]) -> Dict[str, Any]:
    # ensure fields + create stable id
    rid = r.get("id")
    if not rid:
        raw = (r.get("platform","") + (r.get("title") or "") + (r.get("created_at") or ""))
        rid = hashlib.md5(raw.encode()).hexdigest()
    return {
        "id": rid,
        "platform": r.get("platform"),
        "created_at": r.get("created_at"),
        "title": (r.get("title") or "")[:400],
        "text": (r.get("text") or "")[:4000],
        "author": r.get("author"),
        "url": r.get("url"),
        "lang": r.get("lang") or "en",
        "engagement": int(r.get("engagement") or 0),
        "raw_metrics": r.get("raw_metrics") or {},
        "marketing_relevant": bool(r.get("marketing_relevant", False)),
        "category": r.get("category"),
        "matched_keyword": r.get("matched_keyword"),
        "sentiment_compound": float(r.get("sentiment_compound") or 0.0),
    }

import re
def filter_marketing(records: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    if not keywords:
        return records
    escaped = [re.escape(k) for k in keywords if k]
    if not escaped:
        return records
    pattern = r"\b(?:" + "|".join(escaped) + r")\b"
    rx = re.compile(pattern, flags=re.IGNORECASE)
    out = []
    for r in records:
        text = (r.get("title","") or "") + " " + (r.get("text","") or "")
        m = rx.search(text)
        if m:
            r['marketing_relevant'] = True
            r['matched_keyword'] = m.group(0).lower()
            out.append(r)
    return out

# sentiment (VADER)
def add_sentiment(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        import nltk
        from nltk.sentiment import SentimentIntensityAnalyzer
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except Exception:
            nltk.download("vader_lexicon")
        sia = SentimentIntensityAnalyzer()
    except Exception:
        # fallback: naive polarity 0.0
        for r in records:
            r['sentiment_compound'] = float(r.get("sentiment_compound", 0.0))
        return records

    for r in records:
        text = (r.get("title","") or "") + " " + (r.get("text","") or "")
        s = sia.polarity_scores(text)
        r['sentiment_compound'] = float(s.get("compound", 0.0))
    return records

# categorize using keywords.yaml
def categorize(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keys = load_keywords()
    mapping = keys.get("categories", {})
    for r in records:
        text = ((r.get("title","") or "") + " " + (r.get("text","") or "")).lower()
        chosen = None
        for cat, kws in mapping.items():
            if any(k in text for k in kws):
                chosen = cat
                break
        r['category'] = chosen or "uncategorized"
    return records

# --- storage ---
SCHEMA = """
CREATE TABLE IF NOT EXISTS trends (
    id TEXT PRIMARY KEY,
    platform TEXT,
    created_at TEXT,
    title TEXT,
    text TEXT,
    author TEXT,
    url TEXT,
    lang TEXT,
    engagement INTEGER,
    raw_metrics TEXT,
    marketing_relevant INTEGER,
    category TEXT,
    matched_keyword TEXT,
    sentiment_compound REAL,
    inserted_at TEXT DEFAULT (datetime('now'))
);
"""

def init_db():
    _ensure_dirs()
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(SCHEMA)

def upsert_records(records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0
    init_db()
    cnt = 0
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        for r in records:
            cur.execute("""
            INSERT INTO trends (id, platform, created_at, title, text, author, url, lang,
                                engagement, raw_metrics, marketing_relevant, category,
                                matched_keyword, sentiment_compound)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                platform=excluded.platform,
                created_at=excluded.created_at,
                title=excluded.title,
                text=excluded.text,
                author=excluded.author,
                url=excluded.url,
                lang=excluded.lang,
                engagement=excluded.engagement,
                raw_metrics=excluded.raw_metrics,
                marketing_relevant=excluded.marketing_relevant,
                category=excluded.category,
                matched_keyword=excluded.matched_keyword,
                sentiment_compound=excluded.sentiment_compound
            """, (
                r["id"], r["platform"], r["created_at"], r["title"], r["text"], r["author"], r["url"],
                r["lang"], int(r["engagement"]), json.dumps(r.get("raw_metrics") or {}), 1 if r.get("marketing_relevant") else 0,
                r.get("category"), r.get("matched_keyword"), float(r.get("sentiment_compound") or 0.0)
            ))
            cnt += 1
        con.commit()
    return cnt

# --- report ---
def query_last_days(days: int=7) -> pd.DataFrame:
    init_db()
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql_query("SELECT * FROM trends WHERE created_at IS NULL OR created_at >= ? ORDER BY engagement DESC", con, params=(since,))
    return df

def generate_report(days:int=7, out_html: str=None, make_pdf: bool=False) -> str:
    df = query_last_days(days)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    assets_dir = os.path.join(REPORTS_DIR, "assets")

    # charts
    if not df.empty:
        cat_counts = df['category'].value_counts()
        plt.figure()
        cat_counts.plot(kind='bar')
        plt.title('Records per Category')
        plt.tight_layout()
        cat_counts_png = os.path.join(assets_dir, "category_counts.png")
        plt.savefig(cat_counts_png)
        plt.close()

        s = df.groupby('category')['sentiment_compound'].mean().sort_values(ascending=False)
        plt.figure()
        s.plot(kind='bar')
        plt.title('Average Sentiment by Category')
        plt.tight_layout()
        cat_sent_png = os.path.join(assets_dir, "category_sentiment.png")
        plt.savefig(cat_sent_png)
        plt.close()
    else:
        # create empty placeholders
        cat_counts_png = os.path.join(assets_dir, "category_counts.png")
        cat_sent_png = os.path.join(assets_dir, "category_sentiment.png")
        # create tiny blank images so template doesn't break
        for p in (cat_counts_png, cat_sent_png):
            plt.figure(figsize=(2,1)); plt.text(0.5,0.5,"No data",ha="center"); plt.axis('off'); plt.savefig(p); plt.close()

    stats = {'total_records': int(df.shape[0]), 'unique_topics': int(df['title'].nunique()) if not df.empty else 0}
    top_category = df['category'].value_counts().idxmax() if not df.empty else "n/a"
    pos_cat = df.groupby('category')['sentiment_compound'].mean().idxmax() if not df.empty else "n/a"
    cols = ['platform','title','category','engagement','sentiment_compound','created_at','url']
    top_trends = df[cols].head(20).to_dict(orient='records') if not df.empty else []

    period_label = f"Last {days} days"
    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # render template (the templates are in repo reports/templates)
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape(['html','xml']))
    tpl = env.get_template("weekly_report.html.j2")
    html = tpl.render(period_label=period_label, geo=GEO, stats=stats,
                      highlights={'top_category': top_category, 'positive_category': pos_cat, 'top_trend': top_trends[0] if top_trends else {'title':'n/a','platform':'n/a'}},
                      top_trends=top_trends, generated_at=generated_at)

    out_html = out_html or os.path.join(REPORTS_DIR, "weekly_report.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

    if make_pdf:
        try:
            import pdfkit
            pdf_path = out_html.replace(".html", ".pdf")
            pdfkit.from_file(out_html, pdf_path)
        except Exception:
            pass

    return out_html

# --- high-level orchestrator ---
def ingest_and_store(days:int=7) -> int:
    keys = build_keyword_list()
    if MOCK_MODE:
        from samples.make_sample_data import generate_mock_records
        records = generate_mock_records(80)
    else:
        records = extract_all(keys, days=days)
        records = filter_marketing(records, keys)
        records = add_sentiment(records)
        records = categorize(records)
        records = [normalize_record(r) for r in records]
    return upsert_records(records)
