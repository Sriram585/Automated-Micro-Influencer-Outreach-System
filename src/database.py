import sqlite3
import pandas as pd
from src.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS influencers (
        channel_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        platform TEXT NOT NULL,
        profile_url TEXT NOT NULL,
        followers INTEGER NOT NULL,
        engagement_rate REAL NOT NULL,
        niche TEXT,
        content_themes TEXT,
        contact_email TEXT,
        instagram_url TEXT,
        website_url TEXT,
        audience_age TEXT,
        audience_gender TEXT,
        audience_geography TEXT,
        recent_videos TEXT,
        raw_description TEXT,
        filter_status TEXT,
        filter_reason TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outreach_tracker (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        influencer_name TEXT,
        email TEXT,
        email_subject TEXT,
        email_pitch TEXT,
        email_word_count INTEGER,
        instagram_dm TEXT,
        dm_word_count INTEGER,
        sent INTEGER DEFAULT 0,
        sent_date TEXT,
        status TEXT,
        FOREIGN KEY(channel_id) REFERENCES influencers(channel_id)
    )
    """)
    conn.commit()
    conn.close()

def export_datasets_to_csv():
    conn = get_connection()
    
    # 1. Expected Output B: Influencer Dataset (All 8 Mandatory + 5 Optional Fields + Filter Reasons)
    df_inf = pd.read_sql_query("""
        SELECT 
            name AS "Name",
            platform AS "Platform",
            followers AS "Followers",
            engagement_rate AS "Engagement (%)",
            niche AS "Niche",
            contact_email AS "Email",
            profile_url AS "Profile URL",
            content_themes AS "Content Theme",
            instagram_url AS "Instagram / TikTok",
            website_url AS "Website",
            audience_age AS "Audience Age",
            audience_gender AS "Audience Gender",
            audience_geography AS "Audience Geography",
            filter_status AS "Status",
            filter_reason AS "Filter Reason"
        FROM influencers
    """, conn)
    df_inf.to_csv("data/influencers_dataset.csv", index=False)

    # 2. Expected Output C: Personalized Messages
    df_msg = pd.read_sql_query("""
        SELECT 
            influencer_name AS "Influencer",
            email AS "Email",
            email_subject AS "Email Subject",
            email_pitch AS "Email Pitch (60-90 words)",
            email_word_count AS "Email Words",
            instagram_dm AS "Instagram DM (15-30 words)",
            dm_word_count AS "DM Words"
        FROM outreach_tracker
    """, conn)
    df_msg.to_csv("data/personalized_messages.csv", index=False)

    # 3. Expected Output D: Outreach Tracker
    df_track = pd.read_sql_query("""
        SELECT 
            influencer_name AS "Influencer",
            email AS "Email",
            CASE WHEN email_pitch IS NOT NULL THEN 'Yes' ELSE 'No' END AS "Message Generated",
            CASE WHEN sent = 1 THEN 'Yes' ELSE 'No' END AS "Sent",
            COALESCE(sent_date, 'N/A') AS "Date",
            status AS "Status"
        FROM outreach_tracker
    """, conn)
    df_track.to_csv("data/outreach_tracker.csv", index=False)

    # 4. Section 5 Requirement: Simulated / Manual Instagram DM Sending Queue
    df_ig = pd.read_sql_query("""
        SELECT 
            t.influencer_name AS "Influencer",
            i.profile_url AS "Creator Channel URL",
            i.instagram_url AS "Instagram / Social Handle",
            t.instagram_dm AS "Generated Instagram DM (15-30w)",
            t.dm_word_count AS "Word Count",
            CASE 
                WHEN i.instagram_url != 'Not Found' THEN 'READY_FOR_MANUAL_IG_DISPATCH'
                ELSE 'SIMULATED_CREATOR_DM_QUEUED'
            END AS "DM Workflow Status"
        FROM outreach_tracker t
        JOIN influencers i ON t.channel_id = i.channel_id
    """, conn)
    df_ig.to_csv("data/instagram_dm_workflow.csv", index=False)
    conn.close()