from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json


def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({"Message": "Hello, World"})

    @app.route("/api/data", methods=["POST", "GET"])
    def get_data():
        if request.method == "POST":
            id = int(request.json.get("user"))
        else:
            id = 2

        directory = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(directory, "../q-vercel-latency.json")

        with open(data_path) as f:
            data = json.load(f)

        return data[id]

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
