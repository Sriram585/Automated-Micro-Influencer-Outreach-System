import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="EDXSO Influencer Outreach Engine", layout="wide")
st.title("Automated Micro-Influencer Outreach System")
st.caption("End-to-End Discovery, Filtering, Enrichment, Constrained LLM Personalization & Idempotent Outreach Tracker")

if not os.path.exists("data/influencers_dataset.csv"):
    st.warning("No dataset found yet. Run `python main.py` first to populate the database and CSVs.")
    st.stop()

df_inf = pd.read_csv("data/influencers_dataset.csv")
df_msg = pd.read_csv("data/personalized_messages.csv")
df_track = pd.read_csv("data/outreach_tracker.csv")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Discovered Influencers", len(df_inf))
col2.metric("Shortlisted (Passed Filters)", len(df_inf[df_inf["Status"] == "PASSED"]))
col3.metric("Verified Contact Emails", len(df_inf[df_inf["Email"] != "Not Found"]))
col4.metric("Outreach Messages Logged", len(df_track))

tab1, tab2, tab3 = st.tabs([
    "1. Influencer Dataset (Passed & Failed)", 
    "2. AI Personalized Messages (Word-Count Verified)", 
    "3. Outreach Sending & Tracker Log"
])

with tab1:
    st.subheader("Discovered Influencer Dataset (50+ Profiles)")
    status_filter = st.selectbox("Filter by Status:", ["ALL", "PASSED", "FAILED"])
    view_df = df_inf if status_filter == "ALL" else df_inf[df_inf["Status"] == status_filter]
    st.dataframe(view_df, use_container_width=True)

with tab2:
    st.subheader("Dynamic Email Pitches (60–90w) & Instagram DMs (15–30w)")
    st.dataframe(df_msg, use_container_width=True)

with tab3:
    st.subheader("Outreach Sending & Deduplication Log")
    st.dataframe(df_track, use_container_width=True)