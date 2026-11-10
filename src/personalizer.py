from pydantic import BaseModel
from groq import Groq
from src.config import GROQ_API_KEY, BRAND_NAME, BRAND_OFFER

client = Groq(api_key=GROQ_API_KEY)

class OutreachMessages(BaseModel):
    email_subject: str
    email_pitch: str
    instagram_dm: str

def count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w])

def generate_personalized_messages(profile: dict) -> dict:
    feedback = ""
    for attempt in range(4):
        prompt = f"""
        You are an Influencer Partnerships Manager at {BRAND_NAME}.
        Write two highly personalized outreach messages to this creator:
        - Creator Name: {profile['name']}
        - Niche: {profile['niche']}
        - Content Themes: {profile['content_themes']}
        - Recent Videos: {profile['recent_videos']}
        - Followers: {profile['followers']:,} ({profile['engagement_rate']}% engagement)
        - Collaboration Offer: {BRAND_OFFER}

        STRICT WORD COUNT RULES (CRITICAL):
        1. "email_pitch": Must be STRICTLY between 60 and 90 words (count every word including greeting and sign-off). Reference one of their recent videos specifically, mention their audience fit, and propose the collaboration clearly.
        2. "instagram_dm": Must be STRICTLY between 15 and 30 words. Casual, natural, referencing their recent content and proposing a quick chat.

        {feedback}

        Return ONLY valid JSON with keys: "email_subject", "email_pitch", "instagram_dm".
        """
        try:
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            msg = OutreachMessages.model_validate_json(res.choices[0].message.content)
            e_words = count_words(msg.email_pitch)
            dm_words = count_words(msg.instagram_dm)

            if 60 <= e_words <= 90 and 15 <= dm_words <= 30:
                return {
                    "email_subject": msg.email_subject,
                    "email_pitch": msg.email_pitch,
                    "email_word_count": e_words,
                    "instagram_dm": msg.instagram_dm,
                    "dm_word_count": dm_words
                }
            
            feedback = (
                f"PREVIOUS ATTEMPT FAILED WORD COUNT CHECK: "
                f"Your email_pitch was {e_words} words (MUST be 60-90 words). "
                f"Your instagram_dm was {dm_words} words (MUST be 15-30 words). Adjust length immediately."
            )
        except Exception as e:
            feedback = f"JSON Error: {str(e)}"

    # Deterministic fallback trimming/padding if LLM misses after 4 retries
    return _enforce_fallback_bounds(profile)

def _enforce_fallback_bounds(profile: dict) -> dict:
    first_video = profile["recent_videos"].split(" | ")[0]
    email_pitch = (
        f"Hi {profile['name']}, I really enjoyed your recent video, '{first_video}', especially how clearly "
        f"you break down {profile['niche']} concepts for builders. With your engaged audience of {profile['followers']:,} "
        f"developers, we would love to partner with you on {BRAND_OFFER}. We think our workbench aligns naturally "
        f"with your tutorials and offers high value to your viewers. Are you open to a quick chat this week to explore "
        f"a custom sponsorship package? Best regards, Partnerships Team at {BRAND_NAME}"
    )
    instagram_dm = (
        f"Hi {profile['name']}! Loved your recent breakdown on '{first_video[:35]}'. Your {profile['niche']} "
        f"audience is a great fit for {BRAND_NAME}—open to collaborating on a paid sponsorship?"
    )
    return {
        "email_subject": f"Collaboration Inquiry: {profile['name']} x {BRAND_NAME}",
        "email_pitch": email_pitch,
        "email_word_count": count_words(email_pitch),
        "instagram_dm": instagram_dm,
        "dm_word_count": count_words(instagram_dm)
    }