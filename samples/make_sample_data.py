import random, datetime

TOPICS = [
    ("GA4 consent mode v2 impact", "analytics_ai"),
    ("YouTube Shorts CTR hacks", "video_audio"),
    ("TikTok user search growth", "social_media_marketing"),
    ("Meta Advantage+ shopping best practices", "paid_media"),
    ("Newsletter growth via LinkedIn", "content_marketing"),
    ("Google core update volatility", "seo"),
    ("Shopify one-page checkout test", "ecommerce"),
    ("Rebrand case study: B2B SaaS", "branding_pr"),
    ("Local SEO changes in map pack", "local_international"),
    ("Privacy-first attribution models", "privacy_compliance"),
]

def generate_mock_records(n=50):
    out = []
    now = datetime.datetime.utcnow()
    for i in range(n):
        topic, cat = random.choice(TOPICS)
        platform = random.choice(["x","reddit","gtrends"])
        engagement = random.randint(5, 1000)
        created_at = (now - datetime.timedelta(hours=random.randint(0, 24*7))).isoformat()
        out.append({
            "id": f"mock-{platform}-{i}-{random.randint(1000,9999)}",
            "platform": platform,
            "created_at": created_at,
            "title": topic,
            "text": topic + " — discussion and tips",
            "author": None,
            "url": "https://example.com/mock",
            "lang": "en",
            "engagement": engagement,
            "raw_metrics": {"mock": True},
            "marketing_relevant": True,
            "category": cat,
            "matched_keyword": None,
            "sentiment_compound": random.uniform(-0.2, 0.8),
        })
    return out
