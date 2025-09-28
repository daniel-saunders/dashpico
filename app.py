from flask import Flask, request, jsonify, render_template_string
import psycopg
import os
import plotly.graph_objs as go
import plotly.io as pio

app = Flask(__name__)

conn = psycopg.connect(
    host="dpg-d3cnfeogjchc739bkkq0-a",
    dbname="dashpico_logs",
    user="dashpico_logs_user",
    password="Cdx1L02kII4kMq1tsU5Pr2AVrwW6zRpM",
    port=5432
)


# Create table if it doesn't exist
with conn.cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS temps (
            id SERIAL PRIMARY KEY,
            value REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


# logging endpoint
@app.route("/log", methods=["GET"])
def log():
    value = request.args.get("value")
    if value is None:
        return jsonify({"error": "no value provided"}), 400

    with conn.cursor() as cur:
        cur.execute("INSERT INTO temps (value) VALUES (%s)", (float(value),))
        conn.commit()

    app.logger.info(f"Temperature logged: {value}")
    return jsonify({"status": "ok", "value": value})


# inspeection output
@app.route("/print", methods=["GET"])
def print_msg():
    with conn.cursor() as cur:
        cur.execute("SELECT value, created_at FROM temps ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()

    if row:
        value, timestamp = row
        app.logger.info(f"Most recent temperature: {value} at {timestamp}")
        return f"Most recent temperature: {value} at {timestamp}"
    else:
        app.logger.info("No temperature data yet.")
        return "No temperature data yet."


@app.route("/graph", methods=["GET"])
def graph():
    # Fetch last 100 temperature readings
    with conn.cursor() as cur:
        cur.execute("SELECT value, created_at FROM temps ORDER BY created_at DESC LIMIT 100")
        rows = cur.fetchall()

    if not rows:
        return "No temperature data yet."

    # Split into lists for plotting
    rows.reverse()  # oldest first
    values = [row[0] for row in rows]
    timestamps = [row[1] for row in rows]

    # Create interactive Plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=values, mode='lines+markers', name='Temperature'))
    fig.update_layout(
        title="Temperature over time",
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        autosize=True
    )

    # Render as HTML with auto-refresh (every 10 seconds)
    graph_html = pio.to_html(fig, full_html=False)
    html_template = f"""
    <html>
        <head>
            <title>Temperature Graph</title>
            <script>
                // Refresh page every 10 seconds
                setTimeout(function(){{
                    window.location.reload();
                }}, 10000);
            </script>
        </head>
        <body>
            <h1>Temperature Measurements</h1>
            {{% raw %}}
            {graph_html}
            {{% endraw %}}
        </body>
    </html>
    """
    return render_template_string(html_template)



if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
