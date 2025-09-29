from flask import Flask, request, jsonify, render_template_string
import psycopg
import os
import pygal
from datetime import datetime, timedelta


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


import pygal
from flask import render_template_string

@app.route("/graph", methods=["GET"])
def graph():
    # Fetch last 3600 temperature readings (to cover last 24h)
    with conn.cursor() as cur:
        cur.execute("SELECT value, created_at FROM temps ORDER BY created_at DESC LIMIT 3600")
        rows = cur.fetchall()

    if not rows:
        return "No temperature data yet."

    # Filter readings to last 24 hours
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    rows = [row for row in rows if row[1] >= cutoff]

    if not rows:
        return "No temperature data in the last 24 hours."

    # Sort oldest first
    rows.sort(key=lambda r: r[1])
    values = [row[0] for row in rows]
    timestamps = [row[1] for row in rows]

    # Latest reading
    latest_value = values[-1]
    latest_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")

    # Generate x-axis labels every 3 hours
    # Compute 3-hour boundaries in last 24h
    start = cutoff.replace(minute=0, second=0, microsecond=0)
    label_times = [start + timedelta(hours=i*3) for i in range(9)]  # 0h, 3h, ..., 24h

    # Map each timestamp to a label if it's the closest to a 3-hour mark, else empty
    x_labels = []
    label_index = 0
    for ts in timestamps:
        if label_index < len(label_times) and ts >= label_times[label_index]:
            x_labels.append(label_times[label_index].strftime("%H:%M"))
            label_index += 1
        else:
            x_labels.append('')

    # Create Pygal line chart
    line_chart = pygal.Line(
        show_dots=True,
        show_legend=False,
        x_label_rotation=45,
        show_minor_x_labels=False,
        width=800,
        height=400,
        range=(15, 23)
    )
    line_chart.title = "Temperature over the last 24 hours"
    line_chart.x_labels = x_labels
    line_chart.add("Temperature (°C)", values)

    # Render SVG
    chart_svg = line_chart.render(is_unicode=True)

    # Embed SVG in HTML
    html_template = f"""
    <html>
        <head>
            <title>Temperature Graph</title>
        </head>
        <body>
            <h1>Temperature Measurements</h1>
            <h2>Latest: {latest_value} °C at {latest_time}</h2>
            {{% raw %}}
            {chart_svg}
            {{% endraw %}}
        </body>
    </html>
    """
    return render_template_string(html_template)


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
