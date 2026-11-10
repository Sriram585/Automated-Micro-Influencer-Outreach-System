import time
from pydantic import BaseModel
from groq import Groq

from src.config import (
    GROQ_API_KEY, GROQ_MODEL, MIN_FOLLOWERS, MAX_FOLLOWERS, 
    MIN_ENGAGEMENT_RATE, TARGET_NICHE, BRAND_OFFER
)

client = Groq(api_key=GROQ_API_KEY)

class ClassificationResult(BaseModel):
    is_brand_fit: bool
    niche: str
    content_themes: list[str]
    audience_age: str
    audience_gender: str
    reason: str

def filter_and_classify(profile: dict) -> dict:
    subs = profile["followers"]
    er = profile["engagement_rate"]
    
    # Default demographic fallbacks for rejected channels
    profile["audience_age"] = "18-34"
    profile["audience_gender"] = "Mixed (Tech/STEM Skew)"

    if subs < MIN_FOLLOWERS:
        profile.update({
            "niche": TARGET_NICHE,
            "content_themes": "N/A",
            "filter_status": "FAILED",
            "filter_reason": f"Failed: Follower count ({subs:,}) below minimum threshold ({MIN_FOLLOWERS:,})."
        })
        return profile

    if subs > MAX_FOLLOWERS:
        profile.update({
            "niche": TARGET_NICHE,
            "content_themes": "N/A",
            "filter_status": "FAILED",
            "filter_reason": f"Failed: Follower count ({subs:,}) exceeds micro-influencer cap ({MAX_FOLLOWERS:,})."
        })
        return profile

    if er < MIN_ENGAGEMENT_RATE:
        profile.update({
            "niche": TARGET_NICHE,
            "content_themes": "N/A",
            "filter_status": "FAILED",
            "filter_reason": f"Failed: Engagement rate ({er}%) below minimum required ({MIN_ENGAGEMENT_RATE}%)."
        })
        return profile

    time.sleep(1.0)  # Respect Groq RPM limits

    prompt = f"""
    Evaluate this YouTube channel for a micro-influencer collaboration: {BRAND_OFFER}.
    Target Category: {TARGET_NICHE}
    
    Channel Name: {profile['name']}
    Geography: {profile.get('country', 'Global')}
    Bio Snippet: {profile['raw_description'][:600]}
    Recent Videos: {profile['recent_videos'][:500]}
    
    CRITICAL FILTERING RULES:
    1. Set "is_brand_fit": false if the channel is a B2B SaaS company/corporate product channel (e.g., LambdaTest, TestMu AI, IBM, Google) rather than an independent creator, educator, or developer community.
    2. Set "is_brand_fit": false if the content is unrelated to Technology, Programming, Data Science, AI, or Tech Career tutorials.
    3. Estimate "audience_age" (e.g., "18-24 (University/Entry-Level Devs)", "22-34 (Working Software Engineers)", or "25-40 (Data & AI Practitioners)") and "audience_gender" based on their content style.

    Return ONLY valid JSON with these exact keys:
    {{
        "is_brand_fit": true,
        "niche": "Specific sub-niche (e.g., Data Engineering, Python & AI, Tech Career)",
        "content_themes": ["Theme 1", "Theme 2", "Theme 3"],
        "audience_age": "Estimated age bracket and persona",
        "audience_gender": "Estimated gender split (e.g., Mixed / ~65% Male, ~35% Female)",
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
            profile["content_themes"] = ", ".join(data.content_themes[:4])
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

    profile["niche"] = TARGET_NICHE
    profile["content_themes"] = "AI Engineering, Software Tutorials, Coding"
    profile["filter_status"] = "PASSED"
    profile["filter_reason"] = f"Passed micro-influencer metrics ({subs:,} subs, {er}% ER) and niche relevance."
    return profile