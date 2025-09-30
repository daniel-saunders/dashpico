from flask import Flask, request, jsonify, render_template_string, send_file
import psycopg
import os
from datetime import datetime, timedelta
from io import BytesIO
import time


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


from flask import render_template_string
import plotly.graph_objects as go
from datetime import datetime, timedelta


import io
import base64
import matplotlib.pyplot as plt
from flask import render_template_string
from datetime import datetime, timezone, timedelta

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

    print("Query time:", time.time() - t_start)
    if not rows:
        return "No temperature data yet."

    # Sort oldest first
    rows.sort(key=lambda r: r[0])
    timestamps = [r[0] for r in rows]
    values = [r[1] for r in rows]

    # Latest reading
    latest_value = values[-1]
    latest_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")

    # Create Matplotlib figure
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(timestamps, values, marker='o', linestyle='-', color='tab:blue')

    # Fixed Y-axis
    ax.set_ylim(15, 23)

    # Format X-axis: 3-hour intervals
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=False))
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(f"Temperature over last 24 hours (latest {latest_value} °C at {latest_time})")

    fig.autofmt_xdate(rotation=45)

    # Save figure to PNG in memory
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Render HTML
    html_template = f"""
    <html>
        <head><title>Temperature Graph</title></head>
        <body>
            <img src="data:image/png;base64,{img_base64}" alt="Temperature Graph">
        </body>
    </html>
    """

    print("Total time:", time.time() - t_start)
    return render_template_string(html_template)

# @app.route("/graph", methods=["GET"])
# def graph():
#     t_start = time.time()
#     # Fetch readings
#     with conn.cursor() as cur:
#         cur.execute("""
#             WITH ordered AS (
#             SELECT 
#                 value,
#                 created_at,
#                 ROW_NUMBER() OVER (ORDER BY created_at) AS rn
#             FROM temps
#             ORDER BY created_at DESC
#             LIMIT 10800
#         )
#         SELECT
#             created_at,
#             AVG(value) OVER (
#                 ORDER BY rn
#                 ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
#             ) AS rolling_avg
#         FROM ordered
#         WHERE rn % 10 = 0   -- take every 10th row
#         ORDER BY created_at;
#         """)
#         rows = cur.fetchall()

#     print(time.time() - t_start)
#     if not rows:
#         return "No temperature data yet."

#     if not rows:
#         return "No temperature data in the last 24 hours."

#     # Sort oldest first
#     rows.sort(key=lambda r: r[0])
#     values = [r[1] for r in rows]
#     timestamps = [r[0] for r in rows]

#     # Latest reading
#     latest_value = values[-1]
#     latest_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")

#     # Create figure
#     fig = go.Figure()
#     fig.add_trace(go.Scatter(x=timestamps, y=values, mode='lines+markers', name='Temperature'))

#     print(time.time() - t_start)

#     # Y-axis fixed
#     fig.update_yaxes(range=[15, 23])

#     # X-axis: 3-hour intervals
#     fig.update_xaxes(
#         dtick=3*3600*1000,  # milliseconds
#         tickformat="%H:%M",
#         tickangle=45
#     )

#     # Hide legend
#     fig.update_layout(showlegend=False, title=f"Temperature over last 24 hours (latest {latest_value} °C at {latest_time})")

#     # Render HTML
#     graph_html = fig.to_html(full_html=False)
#     html_template = f"""
#     <html>
#         <head>
#             <title>Temperature Graph</title>
#         </head>
#         <body>
#             {graph_html}
#         </body>
#     </html>
#     """

#     print(time.time() - t_start)

#     return render_template_string(html_template)


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
