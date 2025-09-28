# app.py
import dash
from dash import html
from flask import Flask

# Create the Flask server
server = Flask(__name__)

# Add a simple endpoint
@server.route("/hello", methods=["GET"])
def hello():
    return "hello world"

# Wrap it with Dash (optional UI at "/")
app = dash.Dash(__name__, server=server, routes_pathname_prefix="/")
app.layout = html.Div("Hello from Dash root!")

if __name__ == "__main__":
    # Render expects your app to listen on 0.0.0.0 and a port from $PORT
    import os
    app.run_server(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
