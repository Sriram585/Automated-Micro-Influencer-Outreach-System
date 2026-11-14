import argparse
import os
from src.config import YOUTUBE_API_KEY, GROQ_API_KEY, DB_PATH
from src.database import init_db, get_connection, export_datasets_to_csv
from src.discovery import discover_youtube_influencers
from src.enrichment import enrich_influencer_profile
from src.filter import filter_and_classify
from src.personalizer import generate_personalized_messages
from src.sender import process_outreach_sending

def run_pipeline(target_count: int = 65, force_refresh: bool = False):
    print("=== Automated Micro-Influencer Outreach Pipeline ===")
    init_db()

    # Graceful offline/evaluator fallback if API keys are missing
    if not YOUTUBE_API_KEY or not GROQ_API_KEY:
        if os.path.exists(DB_PATH):
            print("[Offline Mode] API keys not detected in .env. Exporting existing SQLite dataset to CSV...")
            export_datasets_to_csv()
            print("Done! Launch `streamlit run app.py` to inspect the pre-populated pipeline.")
            return
        raise RuntimeError("Missing YOUTUBE_API_KEY or GROQ_API_KEY in .env and no cached database found.")

    raw_profiles = discover_youtube_influencers(target_count=target_count)
    conn = get_connection()
    cursor = conn.cursor()

    passed_count = 0
    skipped_cached = 0

    for idx, prof in enumerate(raw_profiles, 1):
        cid = prof["channel_id"]

        # True Automation & Idempotency: Skip expensive scraping & LLM calls if already processed
        if not force_refresh:
            cursor.execute(
                "SELECT i.filter_status, i.contact_email, t.status FROM influencers i "
                "LEFT JOIN outreach_tracker t ON i.channel_id = t.channel_id WHERE i.channel_id = ?",
                (cid,)
            )
            existing = cursor.fetchone()
            if existing and (existing["filter_status"] == "FAILED" or existing["status"] is not None):
                skipped_cached += 1
                if existing["filter_status"] == "PASSED":
                    passed_count += 1
                print(f"[{idx}/{len(raw_profiles)}] SKIPPED (Already Processed): {prof['name']} -> {existing['filter_status']}")
                continue

        print(f"[{idx}/{len(raw_profiles)}] Processing: {prof['name']} ({prof['followers']:,} subs)...")
        
        # 2. Filtering & Classification
        prof = filter_and_classify(prof)
        
        # 3. Profile Enrichment
        prof = enrich_influencer_profile(prof)

        cursor.execute("""
            INSERT OR REPLACE INTO influencers (
                channel_id, name, platform, profile_url, followers, engagement_rate,
                niche, content_themes, contact_email, instagram_url, website_url,
                audience_age, audience_gender, audience_geography, recent_videos,
                raw_description, filter_status, filter_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prof["channel_id"], prof["name"], prof["platform"], prof["profile_url"],
            prof["followers"], prof["engagement_rate"], prof["niche"], prof["content_themes"],
            prof["contact_email"], prof["instagram_url"], prof["website_url"],
            prof["audience_age"], prof["audience_gender"], prof["audience_geography"],
            prof["recent_videos"], prof["raw_description"], prof["filter_status"], prof["filter_reason"]
        ))
        conn.commit()

        # 4. AI Personalization & 5. Sending Layer (Only for PASSED influencers)
        if prof["filter_status"] == "PASSED":
            passed_count += 1
            msg_data = generate_personalized_messages(prof)
            send_status = process_outreach_sending(
                prof["channel_id"], prof["name"], prof["contact_email"], msg_data
            )
            print(f"   -> PASSED | Email: {prof['contact_email']} | Words: {msg_data['email_word_count']}w / {msg_data['dm_word_count']}w | {send_status}")
        else:
            print(f"   -> {prof['filter_reason']}")

    conn.close()
    export_datasets_to_csv()
    print("\n=== Pipeline Complete! ===")
    print(f"Total Discovered: {len(raw_profiles)} | Shortlisted (Passed): {passed_count} | Cached Skips: {skipped_cached}")
    print("Exported files to /data: influencers_dataset.csv, personalized_messages.csv, outreach_tracker.csv, instagram_dm_workflow.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EDXSO Automated Micro-Influencer Outreach Pipeline")
    parser.add_argument("--target", type=int, default=65, help="Target number of influencers to discover (e.g., 65 or 500)")
    parser.add_argument("--force-refresh", action="store_true", help="Re-process channels even if already in SQLite")
    args = parser.parse_args()
    run_pipeline(target_count=args.target, force_refresh=args.force_refresh)