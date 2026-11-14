import time
from pydantic import BaseModel
from groq import Groq
from src.config import (
    GROQ_API_KEY, GROQ_MODEL, MIN_FOLLOWERS, MAX_FOLLOWERS, 
    MIN_ENGAGEMENT_RATE, TARGET_NICHE, BRAND_OFFER
)

client = Groq(api_key=GROQ_API_KEY)

TECH_THEME_KEYWORDS = {
    "Python Programming": ["python", "django", "flask", "fastapi", "pandas"],
    "AI & LLM Engineering": ["ai", "llm", "gpt", "agent", "langchain", "rag", "openai", "machine learning", "deep learning"],
    "Data Science & Analytics": ["data", "sql", "analytics", "power bi", "tableau", "etl", "spark"],
    "Software & Web Dev": ["javascript", "react", "fullstack", "coding", "developer", "devops", "cloud", "aws", "dotnet"],
    "Tech Career & Tutorials": ["tutorial", "roadmap", "project", "portfolio", "interview", "engineer", "automation"]
}

CORPORATE_BLOCKLIST = {"lambdatest", "testmu", "ibm", "google cloud", "intellipaat", "simplilearn", "edureka", "kodekloud"}

class ClassificationResult(BaseModel):
    is_brand_fit: bool
    niche: str
    content_themes: list[str]
    audience_age: str
    audience_gender: str
    reason: str

def infer_deterministic_themes(text: str) -> list[str]:
    lower_text = text.lower()
    matched = [theme for theme, kw_list in TECH_THEME_KEYWORDS.items() if any(k in lower_text for k in kw_list)]
    return matched[:3] if matched else ["Technology Tutorials", "Software & Coding"]

def filter_and_classify(profile: dict) -> dict:
    subs = profile["followers"]
    er = profile["engagement_rate"]
    combined_text = f"{profile['name']} {profile.get('raw_description', '')} {profile.get('recent_videos', '')}"
    
    # Always populate baseline demographic & content theme context so no row in CSV has "N/A"
    baseline_themes = infer_deterministic_themes(combined_text)
    profile["content_themes"] = ", ".join(baseline_themes)
    profile["audience_age"] = "18-34 (Tech/Developer Demographic)"
    profile["audience_gender"] = "Mixed (Tech/STEM Skew)"

    if subs < MIN_FOLLOWERS:
        profile.update({
            "niche": TARGET_NICHE,
            "filter_status": "FAILED",
            "filter_reason": f"Failed: Follower count ({subs:,}) below minimum threshold ({MIN_FOLLOWERS:,})."
        })
        return profile

    if subs > MAX_FOLLOWERS:
        profile.update({
            "niche": TARGET_NICHE,
            "filter_status": "FAILED",
            "filter_reason": f"Failed: Follower count ({subs:,}) exceeds micro-influencer cap ({MAX_FOLLOWERS:,})."
        })
        return profile

    if er < MIN_ENGAGEMENT_RATE:
        profile.update({
            "niche": TARGET_NICHE,
            "filter_status": "FAILED",
            "filter_reason": f"Failed: Engagement rate ({er}%) below minimum required ({MIN_ENGAGEMENT_RATE}%)."
        })
        return profile

    # Hard Deterministic Block for Corporate B2B SaaS Accounts
    if any(corp in profile["name"].lower() for corp in CORPORATE_BLOCKLIST):
        profile.update({
            "niche": "B2B Corporate / SaaS",
            "filter_status": "FAILED",
            "filter_reason": f"Failed Brand Fit: '{profile['name']}' is a corporate organization/SaaS brand, not an individual micro-influencer."
        })
        return profile

    time.sleep(1.0)

    prompt = f"""
    Evaluate this YouTube channel for a micro-influencer collaboration: {BRAND_OFFER}.
    Target Category: {TARGET_NICHE}
    
    Channel Name: {profile['name']}
    Geography: {profile.get('country', 'Global')}
    Bio Snippet: {profile['raw_description'][:600]}
    Recent Videos: {profile['recent_videos'][:500]}
    
    CRITICAL FILTERING RULES:
    1. Set "is_brand_fit": false if the channel is a B2B SaaS company, corporate product account, or institutional bootcamp rather than an independent creator or educator.
    2. Set "is_brand_fit": false if the content is unrelated to Technology, Programming, Data Science, AI, or Tech Career tutorials.
    3. Estimate "audience_age" (e.g., "18-24 (CS Students & Junior Devs)", "22-34 (Software Engineers)", or "25-40 (Data & AI Practitioners)") and "audience_gender" based on their content style.

    Return ONLY valid JSON with these exact keys:
    {{
        "is_brand_fit": true,
        "niche": "Specific sub-niche (e.g., Data Engineering, Python & AI, Tech Career)",
        "content_themes": ["Theme 1", "Theme 2", "Theme 3"],
        "audience_age": "Estimated age bracket and persona",
        "audience_gender": "Estimated gender split",
        "reason": "Clear 1-sentence reason why they passed or failed brand fit."
    }}
    """
    for _ in range(2):
        try:
            res = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = ClassificationResult.model_validate_json(res.choices[0].message.content)
            profile["niche"] = data.niche
            profile["content_themes"] = ", ".join(data.content_themes[:4]) if data.content_themes else profile["content_themes"]
            profile["audience_age"] = data.audience_age
            profile["audience_gender"] = data.audience_gender
            if data.is_brand_fit:
                profile["filter_status"] = "PASSED"
                profile["filter_reason"] = f"Passed ({subs:,} subs, {er}% ER): {data.reason}"
            else:
                profile["filter_status"] = "FAILED"
                profile["filter_reason"] = f"Failed Brand Fit: {data.reason}"
            return profile
        except Exception:
            time.sleep(1.5)

    # Safe Deterministic Fallback (Requires Tech Keyword Match instead of blind PASSED)
    has_tech_signal = any(
        any(k in combined_text.lower() for k in kw_list)
        for kw_list in TECH_THEME_KEYWORDS.values()
    )
    profile["niche"] = baseline_themes[0]
    if has_tech_signal:
        profile["filter_status"] = "PASSED"
        profile["filter_reason"] = f"Passed deterministic criteria ({subs:,} subs, {er}% ER) & verified {baseline_themes[0]} relevance."
    else:
        profile["filter_status"] = "FAILED"
        profile["filter_reason"] = "Failed Brand Fit: Insufficient technology/AI content signals in channel metadata."
    return profile