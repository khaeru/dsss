from flask import Flask, request

app = Flask(__name__)


@app.route("/")
def index():
    return "<p>Hello, World!</p>"


@app.route("/<resource>/<agency_id>/<resource_id>/<version>/<item_id>")
def structure(resource, agency_id, resource_id, version, item_id):
    return (
        "Structure endpoint<br/>"
        + ", ".join([resource, agency_id, resource_id, version, item_id])
        + "<br/>"
        + repr(request.args)
    )


@app.route("/<resource>/<flow_ref>/<key>/<provider_ref>")
def data(resource, flow_ref, key, provider_ref):
    return (
        "Data endpoint<br/>"
        + ", ".join([resource, flow_ref, key, provider_ref])
        + "<br/>"
        + repr(request.args)
    )


@app.cli.command()
def demo():
    """Run a local demo server."""
    app.run(debug=True)
