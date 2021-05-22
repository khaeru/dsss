"""Information defined in the SDMX REST web service standard.

.. todo:: Move to the sdmx1 package.
"""

#: SDMX MIME types.
MIME = {
    "SDMX-ML Generic Data": "application/vnd.sdmx.genericdata+xml;version=2.1",
    "SDMX-ML StructureSpecific Data": (
        "application/vnd.sdmx.structurespecificdata+xml;version=2.1"
    ),
    "SDMX-JSON Data": "application/vnd.sdmx.data+json;version=1.0.0",
    "SDMX-CSV Data": "application/vnd.sdmx.data+csv;version=1.0.0",
    "SDMX-ML Structure": "application/vnd.sdmx.structure+xml;version=2.1",
    "SDMX-JSON Structure": "application/vnd.sdmx.structure+json;version=1.0.0",
    "SDMX-ML Schemas": "application/vnd.sdmx.schema+xml;version=2.1",
    "SDMX-ML Generic Metadata": "application/vnd.sdmx.genericmetadata+xml;version=2.1",
    "SDMX-ML StructureSpecific Meta": (
        "application/vnd.sdmx.structurespecificmetadata+xml;version=2.1"
    ),
}

#: SDMX response codes.
RESPONSE_CODE = {
    200: "OK",
    304: "No change",
    400: "Syntax error",
    401: "Login needed",
    403: "Semantic error",
    404: "Not found",
    406: "Invalid format",
    413: "Results too large",
    414: "URI too long",
    500: "Server error",
    501: "Not implemented",
    503: "Unavailable",
}
