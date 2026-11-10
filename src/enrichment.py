import re
import httpx
from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
URL_REGEX = re.compile(r"https?://[^\s<>\"']+")
IG_REGEX = re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.-]+)")

IGNORED_EMAIL_DOMAINS = {"example.com", "domain.com", "email.com", "yoursite.com", "sentry.io"}
IGNORED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".js", ".css")

def normalize_obfuscated_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s*[\[\(]?\s*at\s*[\]\)]?\s*", "@", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[\[\(]?\s*dot\s*[\]\)]?\s*", ".", cleaned, flags=re.IGNORECASE)
    return cleaned

def extract_valid_email(text: str) -> str:
    for candidate in EMAIL_REGEX.findall(normalize_obfuscated_text(text)):
        candidate = candidate.strip(".,;:)").lower()
        domain = candidate.split("@")[-1]
        if domain not in IGNORED_EMAIL_DOMAINS and not candidate.endswith(IGNORED_EXTENSIONS):
            return candidate
    return "Not Found"

def enrich_influencer_profile(profile: dict) -> dict:
    desc = profile.get("raw_description", "")
    
    # 1. Direct Email Extraction from Bio
    email = extract_valid_email(desc)
    
    # 2. Extract Social & Website Links
    urls = URL_REGEX.findall(desc)
    ig_match = IG_REGEX.search(desc)
    instagram_url = f"https://instagram.com/{ig_match.group(1)}" if ig_match else "Not Found"
    
    website_url = "Not Found"
    for u in urls:
        if not any(s in u.lower() for s in ["youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com", "tiktok.com"]):
            website_url = u.rstrip(".,;)")
            break

    # 3. Crawl External Website/Linktree if Email Not Found in Bio
    if email == "Not Found" and website_url != "Not Found":
        try:
            with httpx.Client(timeout=4.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = client.get(website_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Check mailto links first
                    for a in soup.select("a[href^='mailto:']"):
                        m_email = a["href"].replace("mailto:", "").split("?")[0].strip()
                        if EMAIL_REGEX.match(m_email):
                            email = m_email.lower()
                            break
                    if email == "Not Found":
                        email = extract_valid_email(soup.get_text(" ", strip=True))
        except Exception:
            pass

    profile["contact_email"] = email
    profile["instagram_url"] = instagram_url
    profile["website_url"] = website_url
    profile["audience_age"] = "18-34 (Tech/Developer Demographic)"
    profile["audience_gender"] = "Mixed"
    profile["audience_geography"] = profile.get("country", "Global")
    return profile