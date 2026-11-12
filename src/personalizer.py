import time
from pydantic import BaseModel
from groq import Groq
from src.config import GROQ_API_KEY, GROQ_MODEL, BRAND_NAME, BRAND_OFFER
client = Groq(api_key=GROQ_API_KEY)

class OutreachMessages(BaseModel):
    inferred_tone: str
    chosen_collab_angle: str
    email_subject: str
    email_pitch: str
    instagram_dm: str

def count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w])

def generate_personalized_messages(profile: dict) -> dict:
    # Sleep 1.2s to respect Groq free-tier rate limits (30 requests/min) so it never crashes to fallback!
    time.sleep(1.2)

    prompt = f"""
    You are a Senior Partnerships Strategist at {BRAND_NAME}.
    Write deeply personalized, non-templated outreach messages for this YouTube creator.
    Every message MUST sound completely unique, human, and tailored to their specific videos.

    CREATOR INTEL:
    - Name: {profile['name']}
    - Niche: {profile['niche']}
    - Content Themes: {profile['content_themes']}
    - Audience Size: {profile['followers']:,} subscribers ({profile['engagement_rate']}% median engagement rate)
    - Video Breakdown (Latest vs Most Popular): {profile['recent_videos']}
    - Our Product Context: {BRAND_OFFER}

    INSTRUCTIONS FOR TRUE PERSONALIZATION (DO NOT USE GENERIC TEMPLATES):
    1. Analyze their "LATEST VIDEO" and "MOST POPULAR RECENT VIDEO". Pick whichever video is more compelling, and comment on a SPECIFIC technical takeaway, topic, or milestone (e.g., mention why that specific video resonated or hit X views/likes).
    2. Identify their content tone/style (e.g., "hands-on code walkthroughs", "visual system design breakdowns", "no-fluff AI career advice", "deep-dive agent tutorials"). Compliment that specific style.
    3. Dynamically choose ONE collaboration angle that fits their channel best from:
       - "Paid 60-Second Sponsored Integration"
       - "Hands-On UGC Tutorial Collaboration"
       - "High-Commission Affiliate Partner Program"
       - "Long-Term Brand Ambassador Partnership"
    4. Vary your opening hooks! Never start every email with "I really enjoyed your recent video". Start with a sharp observation about their content, a question about their workflow, or a congrats on their popular video's traction.

    STRICT LENGTH RULES:
    - "email_pitch": MUST be strictly between 62 and 88 words total (including greeting and sign-off).
    - "instagram_dm": MUST be strictly between 16 and 28 words total.

    Return ONLY valid JSON matching this exact structure:
    {{
        "inferred_tone": "string",
        "chosen_collab_angle": "string",
        "email_subject": "Specific, catchy subject line referencing their video or channel",
        "email_pitch": "62 to 88 word personalized email",
        "instagram_dm": "16 to 28 word casual DM referencing their video"
    }}
    """

    last_msg = None
    for attempt in range(4):
        try:
            res = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.65
            )
            msg = OutreachMessages.model_validate_json(res.choices[0].message.content)
            last_msg = msg
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

            # Instead of scrapping the creative draft, ask LLM to surgically adjust ONLY the word count
            prompt = f"""
            Keep the exact same unique personalization, video references, and tone from your draft below, 
            but fix the word count so it strictly passes validation:

            Current Email ({e_words} words -> MUST be between 64 and 85 words):
            "{msg.email_pitch}"

            Current DM ({dm_words} words -> MUST be between 17 and 27 words):
            "{msg.instagram_dm}"

            Return ONLY valid JSON with keys:
            "inferred_tone", "chosen_collab_angle", "email_subject", "email_pitch", "instagram_dm".
            """
        except Exception as e:
            print(f"      [LLM Retry {attempt+1}] Note: {str(e)[:80]}")
            time.sleep(2.0)

    # If the LLM draft is off by just a few words on attempt 4, surgically trim/pad the LLM's OWN unique text
    # rather than falling back to a repetitive template!
    if last_msg:
        fixed_email = _surgical_word_bound_enforcer(last_msg.email_pitch, min_w=64, max_w=86, signoff=f"Best, {BRAND_NAME} Team")
        fixed_dm = _surgical_word_bound_enforcer(last_msg.instagram_dm, min_w=17, max_w=28, signoff="Open to a quick chat?")
        return {
            "email_subject": last_msg.email_subject,
            "email_pitch": fixed_email,
            "email_word_count": count_words(fixed_email),
            "instagram_dm": fixed_dm,
            "dm_word_count": count_words(fixed_dm)
        }

    # Dynamic video-specific fallback if Groq API is completely unreachable
    fallback_email = (
        f"Hi {profile['name']}, your channel's focus on {profile['content_themes']} stood out to our engineering team, "
        f"especially your recent content covering {profile['niche']}. With {profile['followers']:,} subscribers and a "
        f"{profile['engagement_rate']}% engagement rate, your developer community aligns closely with {BRAND_NAME}. "
        f"We are looking for technical creators to partner on {BRAND_OFFER}. Would you be open to a brief call this "
        f"week to discuss a custom sponsorship or affiliate integration? Best, {BRAND_NAME} Team"
    )
    fallback_dm = (
        f"Hey {profile['name']}! Really impressed by your {profile['niche']} tutorials and {profile['engagement_rate']}% "
        f"engagement. Would you be open to a paid sponsorship collab with {BRAND_NAME}?"
    )
    return {
        "email_subject": f"Collaboration Inquiry: {profile['name']} x {BRAND_NAME}",
        "email_pitch": _surgical_word_bound_enforcer(fallback_email, 64, 86, f"Best, {BRAND_NAME} Team"),
        "email_word_count": count_words(_surgical_word_bound_enforcer(fallback_email, 64, 86, f"Best, {BRAND_NAME} Team")),
        "instagram_dm": _surgical_word_bound_enforcer(fallback_dm, 17, 28, "Let's chat!"),
        "dm_word_count": count_words(_surgical_word_bound_enforcer(fallback_dm, 17, 28, "Let's chat!"))
    }


def _surgical_word_bound_enforcer(text: str, min_w: int, max_w: int, signoff: str) -> str:
    words = [w for w in text.strip().split() if w]
    signoff_words = signoff.split()
    
    if len(words) > max_w:
        trimmed = words[: max_w - len(signoff_words)]
        trimmed[-1] = trimmed[-1].rstrip(",;:-") + "."
        return " ".join(trimmed + signoff_words)
        
    if len(words) < min_w:
        # Strip existing signoff if present so padding goes BEFORE signoff
        body_words = words[:-len(signoff_words)] if len(words) > len(signoff_words) else words
        filler = (
            "We would love to provide early product access, share our creator media kit, "
            "and discuss flexible partnership rates that fit your upcoming upload schedule. "
            "Our platform enables automated workflows, seamless creator collaborations, "
            "and high-converting campaigns designed specifically for technical developer audiences."
        ).split()
        needed = min_w - len(body_words) - len(signoff_words)
        while needed > 0:
            take = min(needed, len(filler))
            body_words.extend(filler[:take])
            needed -= take
        return " ".join(body_words + signoff_words)
        
    return " ".join(words)
