from flask import Flask, request, jsonify, render_template_string, send_file
import psycopg
import os
from datetime import datetime, timedelta
import plotext as plt
from io import BytesIO


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
    # Fetch last 1000 temperature readings
    with conn.cursor() as cur:
        cur.execute("SELECT value, created_at FROM temps ORDER BY created_at DESC LIMIT 1000")
        rows = cur.fetchall()

    if not rows:
        return "No temperature data yet."

    # Filter last 24 hours
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    rows = [row for row in rows if row[1] >= cutoff]

    if not rows:
        return "No temperature data in the last 24 hours."

    rows.sort(key=lambda r: r[1])
    values = [row[0] for row in rows]
    timestamps = [row[1] for row in rows]

    # Convert timestamps to numeric x values (seconds since cutoff)
    x_values = [(ts - cutoff).total_seconds() for ts in timestamps]

    # Generate x-axis ticks every 3 hours
    x_ticks = [i*3600*3 for i in range(9)]  # 0h, 3h, 6h, ..., 24h
    x_labels = [(cutoff + timedelta(seconds=sec)).strftime("%H:%M") for sec in x_ticks]

    # Clear previous plot
    plt.clf()

    # Plot the data
    plt.plot(x_values, values, marker='dot', color='cyan')
    plt.ylim(15, 23)
    plt.title("Temperature over the last 24 hours")
    plt.xlabel("Time")
    plt.ylabel("Temperature (°C)")
    plt.xticks(x_ticks, x_labels)

    # Save to in-memory PNG
    buf = BytesIO()
    plt.canvas_color('default')
    plt.axes_color('default')
    plt.ticks_color('white')
    plt.savefig(buf)
    buf.seek(0)

    return send_file(buf, mimetype='image/png', download_name="temperature.png")


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
