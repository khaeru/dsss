from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "<p>Hello, World!</p>"


@app.cli.command()
def demo():
    """Run a local demo server."""
    app.run(debug=True)
