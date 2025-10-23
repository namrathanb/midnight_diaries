import io
def chatbot_query(df, query, client=None):
    q = query.lower().strip()
    # Ticket-specific queries
    if df is not None and not df.empty:
        ticket_col = None
        for col in df.columns:
            if any(k in col.lower() for k in ["ticket", "id", "case", "issue"]):
                ticket_col = col
                break
        res_col = None
        for col in df.columns:
            if "resolution" in col.lower():
                res_col = col
                break
        if ticket_col and any(word in q for word in ["ticket", "id", "case", "issue"]):
            import re
            num_match = re.search(r"\d+", q)
            if num_match:
                ticket_id = num_match.group()
                mask = df[ticket_col].astype(str).str.contains(ticket_id, case=False, na=False)
                if mask.any():
                    row = df[mask].iloc[0]
                    if res_col and res_col in row:
                        return f"🕒 The resolution time for ticket **{row[ticket_col]}** is **{row[res_col]}**."
                    else:
                        return f"✅ Ticket **{row[ticket_col]}** exists, but resolution time not available."
                else:
                    return f"⚠️ No ticket found with ID '{ticket_id}'."

    # Average/summary queries
    if "average" in q or "mean" in q or "trend" in q:
        if df is not None and not df.empty:
            cat_col = None
            for col in df.columns:
                if any(k in col.lower() for k in ["category", "type", "issue", "priority", "queue", "status"]):
                    cat_col = col
                    break
            for col in df.columns:
                if "resolution" in col.lower():
                    res_col = col
                    break
            if cat_col and res_col:
                avg = df.groupby(cat_col)[res_col].mean(numeric_only=True).sort_values(ascending=False).head(5)
                if not avg.empty:
                    best_cat = avg.idxmax()
                    return f"📊 The category with the highest average resolution time is **{best_cat}** ({avg[best_cat]:.2f} units)."

    # Fallback LLM (first 1000 rows)
    try:
        csv_buffer = io.StringIO()
        df.head(1000).to_csv(csv_buffer, index=False)
        dataset_sample = csv_buffer.getvalue()
        prompt = f"""
You are a data analyst assistant. Answer the user's question directly and concisely.
Dataset sample (up to 1000 rows):
{dataset_sample}
Question: "{query}"
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Chatbot error: {e}"
