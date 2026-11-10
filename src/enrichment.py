import re
import httpx
from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
URL_REGEX = re.compile(r"https?://[^\s<>\"'\)\]]+")
IG_REGEX = re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.-]+)")
TIKTOK_REGEX = re.compile(r"(?:https?://)?(?:www\.)?tiktok\.com/(@[a-zA-Z0-9_.-]+)")

IGNORED_EMAIL_DOMAINS = {
    "example.com", "domain.com", "email.com", "yoursite.com", 
    "sentry.io", "w3.org", "schema.org", "wixpress.com", "googleapis.com"
}
IGNORED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css", ".woff", ".ttf")

def normalize_obfuscated_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s*[\[\(]\s*at\s*[\]\)]\s*", "@", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[\[\(]\s*dot\s*[\]\)]\s*", ".", cleaned, flags=re.IGNORECASE)
    return cleaned

def extract_valid_email(text: str) -> str:
    for candidate in EMAIL_REGEX.findall(normalize_obfuscated_text(text)):
        candidate = candidate.strip(".,;:)'\"/\\").lower()
        domain = candidate.split("@")[-1]
        if (
            domain not in IGNORED_EMAIL_DOMAINS 
            and not candidate.endswith(IGNORED_EXTENSIONS)
            and len(candidate) <= 60
        ):
            return candidate
    return "Not Found"

def enrich_influencer_profile(profile: dict) -> dict:
    desc = profile.get("raw_description", "")
    
    # 1. Direct Email Extraction from Bio + Recent Video Descriptions
    email = extract_valid_email(desc)
    
    # 2. Extract Instagram & TikTok Handles
    urls = URL_REGEX.findall(desc)
    ig_match = IG_REGEX.search(desc)
    tk_match = TIKTOK_REGEX.search(desc)
    
    ig_url = f"https://instagram.com/{ig_match.group(1)}" if ig_match else "Not Found"
    tk_url = f"https://tiktok.com/{tk_match.group(1)}" if tk_match else "Not Found"
    
    # Combine Instagram / TikTok / YouTube for the optional cross-platform field
    social_handles = []
    if ig_url != "Not Found":
        social_handles.append(f"IG: {ig_url}")
    if tk_url != "Not Found":
        social_handles.append(f"TikTok: {tk_url}")
    profile["instagram_url"] = " | ".join(social_handles) if social_handles else "Not Found"
    
    candidate_websites = []
    for u in urls:
        u_clean = u.rstrip(".,;)")
        if not any(s in u_clean.lower() for s in [
            "youtube.com", "youtu.be", "instagram.com", "twitter.com", 
            "x.com", "tiktok.com", "linkedin.com", "discord.gg", "facebook.com", "amzn.to", "bit.ly"
        ]):
            if u_clean not in candidate_websites:
                candidate_websites.append(u_clean)

    website_url = candidate_websites[0] if candidate_websites else "Not Found"

    # 3. Crawl up to 2 External Links if Email Not Found
    if email == "Not Found" and candidate_websites:
        for site in candidate_websites[:2]:
            try:
                with httpx.Client(timeout=4.5, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
                    resp = client.get(site)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for a in soup.select("a[href^='mailto:']"):
                            m_email = a["href"].replace("mailto:", "").split("?")[0].strip()
                            if EMAIL_REGEX.match(m_email):
                                email = m_email.lower()
                                break
                        if email == "Not Found":
                            email = extract_valid_email(soup.get_text(" ", strip=True))
                        if email == "Not Found":
                            email = extract_valid_email(resp.text)
                        if email != "Not Found":
                            website_url = site
                            break
            except Exception:
                continue

    profile["contact_email"] = email
    profile["website_url"] = website_url
    profile["audience_geography"] = profile.get("country", "Global")
    return profile