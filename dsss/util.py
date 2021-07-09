from datetime import datetime
from typing import Tuple

import sdmx
from sdmx.rest import RESPONSE_CODE
from werkzeug.routing import BaseConverter, ValidationError


class SDMXResourceConverter(BaseConverter):
    def __init__(self, url_map, kind):
        super().__init__(url_map)
        assert kind in {"data", "structure"}
        self.data_kind = kind == "data"

    def to_python(self, value: str) -> sdmx.Resource:
        # Check the resource type
        try:
            result = sdmx.Resource(value)

            # If data_kind is True, `value` should be in this set; otherwise not
            assert (
                result in {sdmx.Resource.data, sdmx.Resource.metadata}
            ) is self.data_kind
        except (AssertionError, ValueError):
            raise ValidationError(f"resource={value}")
        else:
            return result


class FlowRefConverter(BaseConverter):
    defaults = [None, "all", "latest"]

    def to_python(self, value: str) -> Tuple[str, str, str]:
        result = value.split(",")

        if len(result) > 3:
            raise ValidationError(f"flow_ref={value}")

        L = len(result)
        return tuple(result + self.defaults[L:])


def add_footer_text(msg, texts):
    if msg.footer is None:
        msg.footer = sdmx.message.Footer()

    for text in texts:
        msg.footer.text.append(sdmx.model.InternationalString(text))


def finalize_message(msg):
    # Set the prepared time
    msg.header.prepared = datetime.now()


def gen_error_message(code, text):
    msg = sdmx.message.ErrorMessage(footer=sdmx.message.Footer(code=code))
    add_footer_text(msg, [f"{RESPONSE_CODE[code]}: {text}"])
    return sdmx.to_xml(msg)


def not_implemented_options(defaults, **values):
    """Generate footer text for not implemented query parameters in `values`."""
    for name, value in values.items():
        if value != defaults[name]:
            yield (
                f"Warning: ignored not implemented query parameter {name}={value}"
                + ("" if defaults[name] is None else f" != {repr(defaults[name])}")
            )


def not_implemented_path(defaults, **values):
    """Generate footer text for not implemented path parts in `values`."""
    for name, value in values.items():
        if value != defaults[name]:
            yield (
                f"Warning: ignored not implemented path part "
                f"{name}={value} != {repr(defaults[name])}"
            )
