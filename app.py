from flask import Flask, request, jsonify

app = Flask(__name__)

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
