import json
from pydantic import BaseModel, Field
from groq import Groq
from src.config import (
    GROQ_API_KEY, MIN_FOLLOWERS, MAX_FOLLOWERS, 
    MIN_ENGAGEMENT_RATE, TARGET_NICHE, BRAND_OFFER
)

client = Groq(api_key=GROQ_API_KEY)

class ClassificationResult(BaseModel):
    is_brand_fit: bool = Field(description="True if creator fits Technology, AI, Coding, or Fintech.")
    niche: str = Field(description="Specific sub-niche, e.g., AI Engineering, Python Tutorials, DevTools.")
    content_themes: list[str] = Field(description="3 to 4 key content themes based on recent videos.")
    reason: str = Field(description="Clear 1-sentence reason why the creator passed or failed brand fit.")

def filter_and_classify(profile: dict) -> dict:
    subs = profile["followers"]
    er = profile["engagement_rate"]

    # Stage 1: Deterministic Follower & Engagement Filter
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

    # Stage 2: LLM Brand-Fit & Content Relevance Classification
    prompt = f"""
    Evaluate this YouTube creator for a brand collaboration: {BRAND_OFFER}.
    Target Category: {TARGET_NICHE}
    
    Channel Name: {profile['name']}
    Bio: {profile['raw_description'][:500]}
    Recent Videos: {profile['recent_videos']}
    
    Return ONLY valid JSON matching this schema:
    {{
        "is_brand_fit": true or false,
        "niche": "string",
        "content_themes": ["theme1", "theme2", "theme3"],
        "reason": "1 sentence explanation of why they pass or fail brand fit"
    }}
    """
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = ClassificationResult.model_validate_json(res.choices[0].message.content)
        profile["niche"] = data.niche
        profile["content_themes"] = ", ".join(data.content_themes)
        if data.is_brand_fit:
            profile["filter_status"] = "PASSED"
            profile["filter_reason"] = f"Passed: Micro-influencer criteria met ({subs:,} subs, {er}% ER) & {data.reason}"
        else:
            profile["filter_status"] = "FAILED"
            profile["filter_reason"] = f"Failed Brand Fit: {data.reason}"
    except Exception as e:
        profile["niche"] = TARGET_NICHE
        profile["content_themes"] = "Software Engineering, AI Tutorials"
        profile["filter_status"] = "PASSED"
        profile["filter_reason"] = f"Passed deterministic criteria ({subs:,} subs, {er}% ER); fallback classification applied."

    return profile