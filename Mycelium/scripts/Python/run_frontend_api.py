from flask import Flask, send_from_directory
from flask_cors import CORS
from pathlib import Path
import os

# import the blueprint
from frontend_api import bp  # file is in same directory

# create app without default static folder to serve our frontend dir explicitly
app = Flask(__name__, static_folder=None)
CORS(app)  # allow requests from the frontend served from file:// or another host
app.register_blueprint(bp)

# serve the lightweight frontend files from scripts/frontend
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_frontend(path):
    safe_path = Path(path).as_posix()
    return send_from_directory(str(FRONTEND_DIR), safe_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9002"))
    app.run(host="0.0.0.0", port=port, debug=True)