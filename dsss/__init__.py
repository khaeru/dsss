import json
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, abort, render_template, request
import sdmx

app = Flask(__name__)

# Use templates from within the package
app.template_folder = Path(__file__).parent.joinpath("template")


@app.route("/")
def index():
    # TODO configure the templates path app-wide
    return render_template("index.html")


# MIME types
# SDMX-ML Generic Data
# application/vnd.sdmx.genericdata+xml;version=2.1
# SDMX-ML StructureSpecific Data
# application/vnd.sdmx.structurespecificdata+xml;version=2.1
# SDMX-JSON Data
# application/vnd.sdmx.data+json;version=1.0.0
# SDMX-CSV Data
# application/vnd.sdmx.data+csv;version=1.0.0
# SDMX-ML Structure
# application/vnd.sdmx.structure+xml;version=2.1
# SDMX-JSON Structure
# application/vnd.sdmx.structure+json;version=1.0.0
# SDMX-ML Schemas
# application/vnd.sdmx.schema+xml;version=2.1
# SDMX-ML Generic Metadata
# application/vnd.sdmx.genericmetadata+xml;version=2.1
# SDMX-ML StructureSpecific Meta
# application/vnd.sdmx.structurespecificmetadata+xml;version=2.1


@app.route("/<resource>/<agency_id>/<resource_id>/<version>/<item_id>")
def structure(resource, agency_id, resource_id, version, item_id):
    # Check the resource type
    # TODO reimplement as a flask 'converter'
    try:
        resource = sdmx.Resource(resource)
        assert resource not in {sdmx.Resource.data, sdmx.Resource.metadata}
    except (AssertionError, KeyError):
        abort(404)

    # Prepare a mutable copy of immutable request.args
    args = dict(request.args)

    # Set default values and check the two recognized query parameters
    args.setdefault("detail", "full")

    assert args["detail"] in {
        "allstubs",
        "referencestubs",
        "allcompletestubs",
        "referencecompletestubs",
        "referencepartial",
        "full",
    }

    args.setdefault("references", "none")

    assert args["references"] in {
        "none",
        "parents",
        "parentsandsiblings",
        "children",
        "descendants",
        "all",
    }

    msg = sdmx.read_sdmx(app.config["data_path"] / f"{agency_id}-structure.xml")
    # TODO filter contents
    # TODO cache pickled objects

    msg.header.prepared = datetime.now()

    if msg.footer is None:
        msg.footer = sdmx.message.Footer()

    msg.footer.text.append(
        ", ".join(
            map(
                repr,
                [resource, agency_id, resource_id, version, item_id, request.args],
            )
        )
    )

    return Response(
        sdmx.to_xml(msg),
        content_type="application/vnd.sdmx.structure+xml;version=2.1",
    )


@app.route("/<resource>/<flow_ref>/<key>/<provider_ref>")
def data(resource, flow_ref, key, provider_ref):
    if resource not in {"data", "metadata"}:
        abort(404)

    request.args

    h = sdmx.message.Header(prepared=datetime.now())
    f = sdmx.message.Footer(
        text=[
            ", ".join(map(repr, [resource, flow_ref, key, provider_ref, request.args]))
        ]
    )
    msg = sdmx.message.DataMessage(header=h, footer=f)

    return Response(
        sdmx.to_xml(msg, pretty_print=True),
        content_type="application/vnd.sdmx.genericdata+xml;version=2.1",
    )


@app.cli.command()
def demo():
    """Run a local demo server."""
    # Path containing data
    # TODO read from a configuration file per
    #      https://flask.palletsprojects.com/en/2.0.x/config/
    app.config["data_path"] = Path.cwd() / "data"

    app.run(debug=True)
