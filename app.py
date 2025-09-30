from flask import Flask, request, jsonify, render_template_string, send_file
import psycopg
import os
from datetime import datetime, timedelta
import time
import plotly.graph_objects as go
import json


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
    t_start = time.time()

    # Fetch readings
    with conn.cursor() as cur:
        cur.execute("""
            WITH ordered AS (
                SELECT 
                    value,
                    created_at,
                    ROW_NUMBER() OVER (ORDER BY created_at) AS rn
                FROM temps
                ORDER BY created_at DESC
                LIMIT 10800
            )
            SELECT
                created_at,
                AVG(value) OVER (
                    ORDER BY rn
                    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                ) AS rolling_avg
            FROM ordered
            WHERE rn % 10 = 0
            ORDER BY created_at;
        """)
        rows = cur.fetchall()

    print(time.time() - t_start)
    if not rows:
        return "No temperature data yet."

    # Sort oldest first
    rows.sort(key=lambda r: r[0])
    rolling_values = [r[1] for r in rows]
    timestamps = [r[0] for r in rows]

    # Latest reading
    latest_value = rolling_values[-1]
    latest_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")

    # Also fetch the last 30 actual readings for another trace
    with conn.cursor() as cur:
        cur.execute("""
            SELECT value, created_at
            FROM temps
            ORDER BY created_at DESC
            LIMIT 30
        """)
        last30 = cur.fetchall()

    # Sort oldest first
    last30.sort(key=lambda r: r[1])
    last30_values = [r[0] for r in last30]
    last30_times = [r[1] for r in last30]

    # Create figure
    fig = go.Figure()

    # Rolling average trace (semi-transparent, no markers)
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=rolling_values,
        mode='lines',  # no markers
        name='Rolling Avg',
        line=dict(color='blue', width=2),
        opacity=0.6
    ))

    # Last 30 actual points trace (with markers)
    fig.add_trace(go.Scatter(
        x=last30_times,
        y=last30_values,
        mode='lines+markers',
        name='Last 30 readings',
        line=dict(color='red', width=2)
    ))

    print(time.time() - t_start)

    # Y-axis fixed
    fig.update_yaxes(range=[15, 23])

    # X-axis: 3-hour intervals
    fig.update_xaxes(
        dtick=3*3600*1000,  # milliseconds
        tickformat="%H:%M",
        tickangle=45
    )

    # Hide legend
    fig.update_layout(
        showlegend=False,  # optional: keep legend to distinguish traces
        title=f"Temperature over last 24 hours (latest {latest_value} °C at {latest_time})"
    )

    # Render HTML
    graph_html = fig.to_html(full_html=False)
    html_template = f"""
    <html>
        <head>
            <title>Temperature Graph</title>
        </head>
        <body>
            {graph_html}
        </body>
    </html>
    """
    print(time.time() - t_start)

    return render_template_string(html_template)


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
