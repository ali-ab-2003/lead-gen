"""Streamlit dashboard for browsing generated leads.

Reads directly from Supabase. Run locally with:
    streamlit run dashboard/app.py
or deploy free on Streamlit Community Cloud (set the same secrets there).
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="No-Website Leads", page_icon="📍", layout="wide")


@st.cache_resource
def _client():
    url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("SUPABASE_URL / SUPABASE_KEY not configured.")
        st.stop()
    return create_client(url, key)


@st.cache_data(ttl=300)
def load_leads() -> pd.DataFrame:
    rows = _client().table("leads").select("*").order("lead_score", desc=True).execute().data
    return pd.DataFrame(rows)


st.title("📍 No-Website Lead Generator")

df = load_leads()
if df.empty:
    st.info("No leads yet. Run the pipeline to populate Supabase.")
    st.stop()

# ── Filters ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    areas = st.multiselect("Area", sorted(df["area"].dropna().unique()))
    cats = st.multiselect("Category", sorted(df["category"].dropna().unique()))
    statuses = st.multiselect("Status", sorted(df["status"].dropna().unique()))
    only_email = st.checkbox("Has email", value=False)
    only_owner = st.checkbox("Has owner name", value=False)
    min_score = st.slider("Min lead score", 0, 100, 0)
    if st.button("🔄 Refresh data"):
        load_leads.clear()
        st.rerun()

view = df.copy()
if areas:
    view = view[view["area"].isin(areas)]
if cats:
    view = view[view["category"].isin(cats)]
if statuses:
    view = view[view["status"].isin(statuses)]
if only_email:
    view = view[view["email"].astype(str).str.len() > 0]
if only_owner:
    view = view[view["owner_name"].astype(str).str.len() > 0]
if "lead_score" in view.columns:
    view = view[view["lead_score"].fillna(0) >= min_score]

# ── Metrics ──────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads shown", len(view))
c2.metric("With email", int((view["email"].astype(str).str.len() > 0).sum()))
c3.metric("With owner", int((view["owner_name"].astype(str).str.len() > 0).sum()))
c4.metric("Avg score", round(float(view["lead_score"].dropna().mean()), 1)
          if "lead_score" in view and view["lead_score"].notna().any() else 0)

# ── Table ────────────────────────────────────────────────────────────────
display_cols = [c for c in [
    "lead_score", "name", "category", "area", "phone", "email",
    "owner_name", "rating", "reviews_count", "status", "google_maps_url",
] if c in view.columns]

st.dataframe(
    view[display_cols].sort_values("lead_score", ascending=False)
    if "lead_score" in display_cols else view[display_cols],
    use_container_width=True, hide_index=True,
)

st.download_button(
    "⬇️ Download filtered CSV",
    view.to_csv(index=False).encode("utf-8"),
    file_name="leads_filtered.csv",
    mime="text/csv",
)

# ── Per-lead outreach draft viewer ───────────────────────────────────────
st.subheader("Outreach drafts")
if "name" in view.columns and len(view):
    pick = st.selectbox("Pick a lead", view["name"].tolist())
    row = view[view["name"] == pick].iloc[0]
    st.markdown(f"**Score:** {row.get('lead_score', '—')} — {row.get('score_reason', '')}")
    st.text_area("Draft message", row.get("outreach_draft", ""), height=160)
