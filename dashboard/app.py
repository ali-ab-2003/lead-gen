"""Streamlit dashboard for browsing and tracking generated leads.

Reads (and writes status updates) directly to/from Supabase. Run locally with:
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

st.set_page_config(page_title="Lead Generator", layout="wide")

# Pipeline-tracking statuses the user can tag a lead with.
STATUS_OPTIONS = ["new", "reached out", "interested", "not interested", "converted"]


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


def update_statuses(changes: dict[str, str]) -> None:
    """changes: {place_id: new_status}. Writes each change back to Supabase."""
    client = _client()
    for place_id, status in changes.items():
        client.table("leads").update({"status": status}).eq("place_id", place_id).execute()


st.title("Lead Generator")

df = load_leads()
if df.empty:
    st.info("No leads yet. Run the pipeline to populate Supabase.")
    st.stop()

df["status"] = df["status"].fillna("new").replace("", "new")

# ── Filters ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    areas = st.multiselect("Area", sorted(df["area"].dropna().unique()))
    cats = st.multiselect("Category", sorted(df["category"].dropna().unique()))
    statuses = st.multiselect("Status", sorted(df["status"].dropna().unique()))
    only_email = st.checkbox("Has email", value=False)
    only_owner = st.checkbox("Has owner name", value=False)
    min_score = st.slider("Min lead score", 0, 100, 0)
    if st.button("Refresh data"):
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
c2.metric("Reached out", int((view["status"] != "new").sum()))
c3.metric("With email", int((view["email"].astype(str).str.len() > 0).sum()))
c4.metric("Avg score", round(float(view["lead_score"].dropna().mean()), 1)
          if "lead_score" in view and view["lead_score"].notna().any() else 0)

# ── Editable lead tracker ────────────────────────────────────────────────
st.subheader("Leads")
st.caption("Edit the Status column to tag a lead, then click Save changes.")

editor_cols = [c for c in [
    "name", "category", "area", "phone", "email", "owner_name",
    "lead_score", "rating", "status", "google_maps_url",
] if c in view.columns]

# place_id as the index so we can map edits back to the right row.
editor_df = view.set_index("place_id")[editor_cols]

# Ensure every existing status value is a valid option for the selectbox.
options = STATUS_OPTIONS + [s for s in editor_df["status"].unique() if s not in STATUS_OPTIONS]

edited = st.data_editor(
    editor_df,
    use_container_width=True,
    hide_index=True,
    disabled=[c for c in editor_cols if c != "status"],
    column_config={
        "status": st.column_config.SelectboxColumn("Status", options=options, required=True),
        "lead_score": st.column_config.NumberColumn("Score"),
        "google_maps_url": st.column_config.LinkColumn("Maps", display_text="open"),
    },
    key="lead_editor",
)

# Diff against the originally-loaded statuses to find what changed.
original_status = df.set_index("place_id")["status"]
changes = {
    pid: new
    for pid, new in edited["status"].items()
    if pid in original_status.index and new != original_status.loc[pid]
}

col_save, col_info = st.columns([1, 4])
with col_save:
    if st.button("Save changes", type="primary", disabled=not changes):
        update_statuses(changes)
        load_leads.clear()
        st.success(f"Updated {len(changes)} lead(s).")
        st.rerun()
with col_info:
    if changes:
        st.write(f"{len(changes)} unsaved change(s).")

st.download_button(
    "Download filtered CSV",
    view.to_csv(index=False).encode("utf-8"),
    file_name="leads_filtered.csv",
    mime="text/csv",
)

# ── Per-lead outreach draft viewer ───────────────────────────────────────
st.subheader("Outreach drafts")
if "name" in view.columns and len(view):
    pick = st.selectbox("Pick a lead", view["name"].tolist())
    row = view[view["name"] == pick].iloc[0]
    st.markdown(f"**Score:** {row.get('lead_score', '-')} - {row.get('score_reason', '')}")
    st.text_area("Draft message", row.get("outreach_draft", ""), height=160)
