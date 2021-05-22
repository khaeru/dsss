from datetime import datetime

import sdmx
from werkzeug.routing import BaseConverter, ValidationError


class SDMXResourceConverter(BaseConverter):
    def __init__(self, url_map, kind):
        super().__init__(url_map)
        assert kind in {"data", "structure"}
        self.data_kind = kind == "data"

    def to_python(self, value):
        # Check the resource type
        try:
            sdmx.Resource(value)

            # If data_kind is True, `value` should be in this set; otherwise not
            assert (
                value in {sdmx.Resource.data, sdmx.Resource.metadata}
            ) is self.data_kind
        except (AssertionError, KeyError):
            raise ValidationError
        else:
            return value


def finalize_message(msg, footer_info):
    # Set the prepared time
    msg.header.prepared = datetime.now()

    if msg.footer is None:
        msg.footer = sdmx.message.Footer()

    msg.footer.text.append(
        sdmx.model.InternationalString(
            "DSSS received or interpreted the request with path parts/query parameters:\n"
            + ", ".join(map(repr, footer_info))
        )
    )
