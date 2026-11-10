import streamlit as st
import pandas as pd
import os
from datetime import datetime, timezone
from src.database import get_connection, export_datasets_to_csv

st.set_page_config(page_title="EDXSO Influencer Outreach Engine", layout="wide")
st.title("Automated Micro-Influencer Outreach System")
st.caption("Workflow: Discovery → Data Collection → Filtering → Enrichment → AI Personalization → Review → Sending → Tracking")

if not os.path.exists("data/influencers_dataset.csv"):
    st.warning("No dataset found yet. Run `python main.py` first to populate the database and CSVs.")
    st.stop()

df_inf = pd.read_csv("data/influencers_dataset.csv")
df_msg = pd.read_csv("data/personalized_messages.csv")
df_track = pd.read_csv("data/outreach_tracker.csv")
df_ig = pd.read_csv("data/instagram_dm_workflow.csv") if os.path.exists("data/instagram_dm_workflow.csv") else pd.DataFrame()

col1, col2, col3, col4 = st.columns(4)
col1.metric("1. Discovered Profiles", len(df_inf))
col2.metric("2. Passed Filtering", len(df_inf[df_inf["Status"] == "PASSED"]))
col3.metric("3. Verified Emails Found", len(df_inf[df_inf["Email"] != "Not Found"]))
col4.metric("4. Outreach Logged", len(df_track))

tab1, tab2, tab3, tab4 = st.tabs([
    "1. Influencer Dataset (All 13 Enriched Fields)", 
    "2. AI Personalized Messages (60-90w & 15-30w)", 
    "3. Human Review & Manual/Simulated DM Queue",
    "4. Outreach Tracker & Deduplication Log"
])

with tab1:
    st.subheader("Discovered & Enriched Influencer Dataset (50+ Profiles)")
    status_filter = st.selectbox("Filter by Classification Status:", ["ALL", "PASSED", "FAILED"])
    view_df = df_inf if status_filter == "ALL" else df_inf[df_inf["Status"] == status_filter]
    st.dataframe(view_df, use_container_width=True)

with tab2:
    st.subheader("Dynamic Email Pitches (60–90w) & Instagram DMs (15–30w)")
    st.dataframe(df_msg, use_container_width=True)

with tab3:
    st.subheader("Review & Simulated/Manual Instagram DM Sending Layer")
    st.info("Per Meta API compliance rules, Instagram DMs are queued here for human review and 1-click simulated/manual dispatch.")
    if not df_ig.empty:
        st.dataframe(df_ig, use_container_width=True)
    selected_creator = st.selectbox("Select Shortlisted Creator to Review & Simulate DM Send:", df_track["Influencer"].tolist())
    if st.button("Approve & Simulate Manual DM Dispatch"):
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        conn = get_connection()
        conn.execute(
            "UPDATE outreach_tracker SET sent = 1, sent_date = ?, status = 'SIMULATED_DM_DISPATCHED (Reviewed)' WHERE influencer_name = ?",
            (now_str, selected_creator)
        )
        conn.commit()
        conn.close()
        export_datasets_to_csv()
        st.success(f"Outreach marked as Reviewed & Dispatched for {selected_creator}! Refreshing tracker...")
        st.rerun()

with tab4:
    st.subheader("Outreach Sending & Deduplication Log")
    st.dataframe(df_track, use_container_width=True)