from src.database import init_db, get_connection, export_datasets_to_csv
from src.discovery import discover_youtube_influencers
from src.enrichment import enrich_influencer_profile
from src.filter import filter_and_classify
from src.personalizer import generate_personalized_messages
from src.sender import process_outreach_sending

def run_pipeline():
    print("=== Automated Micro-Influencer Outreach Pipeline ===")
    init_db()
    
    # 1. Discovery (Fetch 65+ profiles to ensure >50 clean records)
    raw_profiles = discover_youtube_influencers(target_count=65)
    
    conn = get_connection()
    cursor = conn.cursor()

    passed_count = 0
    for idx, prof in enumerate(raw_profiles, 1):
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
    print(f"Total Discovered: {len(raw_profiles)} | Shortlisted (Passed): {passed_count}")
    print("Exported files to /data: influencers_dataset.csv, personalized_messages.csv, outreach_tracker.csv")

if __name__ == "__main__":
    run_pipeline()