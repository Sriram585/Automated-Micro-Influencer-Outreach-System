import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from src.config import SEND_MODE, SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, TEST_RECEIVER_EMAIL
from src.database import get_connection

def process_outreach_sending(channel_id: str, name: str, email: str, msg_data: dict) -> str:
    conn = get_connection()
    cursor = conn.cursor()

    # Check for duplicate outreach
    cursor.execute("SELECT status, sent FROM outreach_tracker WHERE channel_id = ?", (channel_id,))
    existing = cursor.fetchone()
    if existing and existing["sent"] == 1:
        conn.close()
        return "SKIPPED_DUPLICATE"

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if email == "Not Found":
        status = "MANUAL_IG_DM_REQUIRED (Email Not Found)"
        sent_flag = 0
        sent_date = "N/A"
    elif SEND_MODE == "LIVE_SMTP" and SMTP_EMAIL and SMTP_PASSWORD:
        try:
            recipient = TEST_RECEIVER_EMAIL or email
            mime = MIMEText(msg_data["email_pitch"])
            mime["Subject"] = msg_data["email_subject"]
            mime["From"] = SMTP_EMAIL
            mime["To"] = recipient

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.send_message(mime)
            status = f"SENT_SMTP (To: {recipient})"
            sent_flag = 1
            sent_date = now_str
        except Exception as e:
            status = f"FAILED_SMTP: {str(e)[:40]}"
            sent_flag = 0
            sent_date = "N/A"
    else:
        status = "SIMULATED_SENT (Verified Email Ready)"
        sent_flag = 1
        sent_date = now_str

    cursor.execute("""
        INSERT INTO outreach_tracker (
            channel_id, influencer_name, email, email_subject, email_pitch,
            email_word_count, instagram_dm, dm_word_count, sent, sent_date, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            sent = excluded.sent,
            sent_date = excluded.sent_date,
            status = excluded.status
    """, (
        channel_id, name, email, msg_data["email_subject"], msg_data["email_pitch"],
        msg_data["email_word_count"], msg_data["instagram_dm"], msg_data["dm_word_count"],
        sent_flag, sent_date, status
    ))
    conn.commit()
    conn.close()
    return status