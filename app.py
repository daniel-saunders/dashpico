from flask import Flask, request, jsonify, render_template_string
import psycopg
import os
import pygal


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
    timestamps = [row[1].strftime("%H:%M:%S") for row in rows]  # format datetime for axis labels

    # Most recent reading (last after reversing)
    latest_value = values[-1]
    latest_time = rows[-1][1].strftime("%Y-%m-%d %H:%M:%S")

    # Create Pygal line chart
    line_chart = pygal.Line(show_dots=True, x_label_rotation=20)
    line_chart.title = "Temperature over time"
    line_chart.x_labels = timestamps
    line_chart.add("Temperature (°C)", values)

    # Render SVG as string
    chart_svg = line_chart.render(is_unicode=True)
    
    # Embed SVG in HTML, showing latest measurement
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
