from flask import Flask, request, jsonify
import os
import tempfile
import pandas as pd
from utils.column_detection import detect_date_col, detect_category_col, detect_resolution_col, detect_ticket_id_col
from utils.plotting import plot_tickets_per_day, plot_tickets_by_category, plot_resolution_trend
from utils.ai_summary import generate_ai_summary
from utils.chatbot import chatbot_query
import plotly.io as pio
from dotenv import load_dotenv
import io
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient


load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize Autogen client with OpenAI model (gemini-2.5-flash)
model_client = OpenAIChatCompletionClient(
    model="gpt-4o",  # Use the appropriate OpenAI model
    api_key=os.getenv("OPENAI_API_KEY")  # Make sure to add your API key
)

# Asynchronous function to generate AI summary using Autogen
async def generate_ai_summary_async(df, date_col, cat_col, res_col):
    sample_text = df.sample(min(len(df), 5)).to_csv(index=False)
    prompt = f"""
You are an expert data analyst. Analyze the following IT ticket dataset sample.
Columns:
- Date: {date_col}
- Category: {cat_col}
- Resolution Time: {res_col}
Provide a concise summary (under 150 words):
1. Key ticket trends
2. Most frequent issue types
3. Suggestions to improve service

Dataset sample:
{sample_text}
"""
    try:
        # Send the prompt to OpenAI for summary generation
        response = await model_client.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"⚠️ Error generating AI summary: {e}"

@app.route("/analyze", methods=["POST"])
async def analyze():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    suffix = os.path.splitext(f.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name
    try:
        if suffix == ".csv":
            df = pd.read_csv(tmp_path)
        else:
            df = pd.read_excel(tmp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    date_col = detect_date_col(df)
    cat_col = detect_category_col(df)
    res_col = detect_resolution_col(df)
    ticket_col = detect_ticket_id_col(df)

    # Prepare figures
    figs = {}
    if date_col is not None:
        figs["tickets_per_day"] = pio.to_json(plot_tickets_per_day(df.copy(), date_col))
    if cat_col is not None:
        figs["tickets_by_category"] = pio.to_json(plot_tickets_by_category(df.copy(), cat_col))
    if res_col is not None and cat_col is not None and date_col is not None:
        figs["resolution_trend"] = pio.to_json(plot_resolution_trend(df.copy(), date_col, cat_col, res_col))

    # Generate AI summary using Autogen (async)
    summary = await generate_ai_summary_async(df.copy(), date_col, cat_col, res_col)

    # KPIs
    kpis = {
        "total_tickets": int(df.shape[0]),
        "avg_resolution_time": None,
        "peak_category": None
    }
    if res_col is not None:
        kpis["avg_resolution_time"] = round(pd.to_numeric(df[res_col], errors='coerce').mean(), 2)
    if cat_col is not None and cat_col in df.columns and not df[cat_col].isna().all():
        try:
            kpis["peak_category"] = str(df[cat_col].value_counts().idxmax())
        except Exception:
            kpis["peak_category"] = None

    # Send back first 1000 rows for chatbot convenience
    csv_buffer = df.head(1000).to_csv(index=False)

    return jsonify({
        "date_col": date_col,
        "cat_col": cat_col,
        "res_col": res_col,
        "ticket_col": ticket_col,
        "figs": figs,
        "summary": summary,
        "kpis": kpis,
        "dataset_sample_csv": csv_buffer
    })

# Define the chat function (asynchronous)
async def chat():
    data = request.json
    question = data.get("question", "")
    csv_sample = data.get("dataset_sample_csv", "")
    try:
        df = pd.read_csv(io.StringIO(csv_sample))
    except Exception:
        df = pd.DataFrame()

    # Call chatbot_query with dataframe and question using Autogen
    answer = await chatbot_query(df, question, model_client)
    return jsonify({"answer": answer})

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    return chat()

if __name__ == "__main__":
    app.run(port=8000, debug=True)
