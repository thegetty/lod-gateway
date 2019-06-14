#!/usr/bin/env python3

from flask import Flask

app = Flask(__name__)

@app.route("/")
def welcome():
    return "Welcome to the Museum Linked Art Data Service!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int("5000"), debug=True)