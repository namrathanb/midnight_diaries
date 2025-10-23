import streamlit as st
import pandas as pd
import plotly.io as pio
import io
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Ticket Analytics Dashboard", layout="wide")

st.markdown("""
<style>
body {background-color: #f4f5f7;}
.card {background-color:white;padding:15px;border-radius:10px;box-shadow:2px 2px 10px #ccc;margin-bottom:15px;}
.stButton>button {background-color:#4a90e2;color:white;border-radius:5px;padding:0.5rem 1rem;}
</style>
""", unsafe_allow_html=True)

st.title("🎫 Ticket Analytics Dashboard")
st.markdown("Upload a CSV or Excel file and click **Analyze** to generate insights.")

col1, col2, col3 = st.columns([1,2,1])
with col2:
    uploaded_file = st.file_uploader("Upload your dataset", type=["csv", "xlsx", "xls"])
    analyze_btn = st.button("Analyze")

for key in ["df","summary","date_col","cat_col","res_col","ticket_col","dataset_sample_csv","kpis","figs"]:
    if key not in st.session_state:
        st.session_state[key] = None

if uploaded_file and analyze_btn:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    with st.spinner("Uploading and analyzing..."):
        resp = requests.post(f"{BACKEND_URL}/analyze", files=files)
    if resp.status_code != 200:
        st.error(f"Analysis failed: {resp.text}")
    else:
        data = resp.json()
        st.session_state.date_col = data.get("date_col")
        st.session_state.cat_col = data.get("cat_col")
        st.session_state.res_col = data.get("res_col")
        st.session_state.ticket_col = data.get("ticket_col")
        st.session_state.summary = data.get("summary")
        st.session_state.kpis = data.get("kpis")
        st.session_state.dataset_sample_csv = data.get("dataset_sample_csv")
        st.session_state.figs = data.get("figs")
        # also load full dataframe locally for user interactions identical to original
        uploaded_file.seek(0)
        suffix = uploaded_file.name.lower().split('.')[-1]
        if suffix == "csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.session_state.df = df
        st.success("✅ Analysis completed!")

if st.session_state.df is not None:
    df = st.session_state.df
    date_col = st.session_state.date_col
    cat_col = st.session_state.cat_col
    res_col = st.session_state.res_col
    ticket_col = st.session_state.ticket_col
    summary = st.session_state.summary
    kpis = st.session_state.kpis
    figs = st.session_state.figs

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Tickets", df.shape[0])
    if res_col:
        kpi2.metric("Avg Resolution Time", round(pd.to_numeric(df[res_col], errors='coerce').mean(),2))
    else:
        kpi2.metric("Avg Resolution Time", "N/A")
    if cat_col:
        try:
            top_cat = df[cat_col].value_counts().idxmax()
        except Exception:
            top_cat = "N/A"
        kpi3.metric("Peak Category", top_cat)
    else:
        kpi3.metric("Peak Category", "N/A")

    left_col, right_col = st.columns([2,1])
    with left_col:
        st.subheader("📊 Visualizations")
        if figs:
            if "tickets_per_day" in figs:
                fig = pio.from_json(figs["tickets_per_day"])
                st.plotly_chart(fig, use_container_width=True)
            if "tickets_by_category" in figs:
                fig = pio.from_json(figs["tickets_by_category"])
                st.plotly_chart(fig, use_container_width=True)
            if "resolution_trend" in figs:
                fig = pio.from_json(figs["resolution_trend"])
                st.plotly_chart(fig, use_container_width=True)

    with right_col:
        st.subheader("🧠 AI Summary")
        if summary:
            st.markdown(f"<div class='card'>{summary}</div>", unsafe_allow_html=True)

        st.subheader("💬 Chat with Your Dataset")
        user_q = st.text_input("Ask a question (e.g., 'response time for ticket-1001')")
        if user_q:
            with st.spinner("Thinking..."):
                resp = requests.post(f"{BACKEND_URL}/chat", json={
                    "question": user_q,
                    "dataset_sample_csv": st.session_state.dataset_sample_csv
                })
                if resp.status_code==200:
                    ans = resp.json().get("answer")
                else:
                    ans = f"⚠️ Chat error: {resp.text}"
                st.markdown(f"<div class='card'><b>AI:</b> {ans}</div>", unsafe_allow_html=True)
