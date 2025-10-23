import io
def generate_ai_summary(df, date_col, cat_col, res_col, client):
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
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error generating AI summary: {e}"
