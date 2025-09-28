from flask import Flask, request, jsonify
import psycopg

app = Flask(__name__)

conn = psycopg.connect(
    host="dpg-d3cnfeogjchc739bkkq0-a",
    database="dashpico_logs",
    user="dashpico_logs_user",
    password="Cdx1L02kII4kMq1tsU5Pr2AVrwW6zRpM",
    port=5432
)
cur = conn.cursor()

# logging endpoint
@app.route("/log", methods=["GET"])
def log():
    value = request.args.get("value")

    print(f"Data received: {value}")  # server-side logging
    return jsonify({"status": "ok", "value": value})


# inspeection output
@app.route("/print", methods=["GET"])
def print_msg():
    print("This is a test message!")
    return "Printed message on server console!"


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
