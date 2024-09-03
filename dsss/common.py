"""Common code and utilities."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Collection, List, Mapping, Optional, Type

import sdmx
from sdmx.rest.common import RESPONSE_CODE, QueryParameter
from starlette.responses import Response

if TYPE_CHECKING:
    import sdmx.format
    import sdmx.message
    import sdmx.rest.common
    import starlette.background
    import starlette.types

log = logging.getLogger(__name__)


class SDMXResponse(Response):
    """Response containing a :class:`sdmx.message.Message`."""

    message: "sdmx.message.Message"

    def __init__(
        self,
        message: "sdmx.message.Message",
        status_code: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional["starlette.background.BackgroundTask"] = None,
    ):
        self.message = message
        if self.message.header is None:
            self.message.header = sdmx.message.Header()
        if self.message.header.prepared is None:
            self.message.header.prepared = datetime.now()

        # Same as parent class, only without `content`
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.init_headers(headers)

    async def __call__(
        self,
        scope: "starlette.types.Scope",
        receive: "starlette.types.Receive",
        send: "starlette.types.Send",
    ) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )

        if "+xml" in (self.media_type or ""):
            # SDMX-ML
            # TODO Check for v2.1 versus v3.0.0
            try:
                body = sdmx.to_xml(self.message, pretty_print=True)
            except Exception as e:
                body = sdmx.to_xml(
                    gen_error_message(500, f"Error rendering message: {e!r}"),
                    pretty_print=True,
                )
        else:
            # Something else
            body = sdmx.to_xml(
                gen_error_message(501, f"Return media type {self.media_type!r}"),
                pretty_print=True,
            )

        await send({"type": "http.response.body", "body": body})

        if self.background is not None:
            await self.background()


def add_footer_text(msg, texts):
    if msg.footer is None:
        msg.footer = sdmx.message.Footer()

    for text in texts:
        msg.footer.text.append(sdmx.model.InternationalString(text))


def gen_error_message(code: int, text: str) -> "sdmx.message.ErrorMessage":
    msg = sdmx.message.ErrorMessage(footer=sdmx.message.Footer(code=code))
    add_footer_text(msg, [f"{RESPONSE_CODE[code]}: {text}"])
    return msg


def gen_error_response(code: int, text: str = "") -> SDMXResponse:
    return SDMXResponse(gen_error_message(code, text), status_code=code)


def handle_media_type(
    supported: List["sdmx.format.MediaType"], value: Optional[str]
) -> str:
    if value is None or "*/*" in value:
        value = repr(supported[0])
    elif not any(value == repr(s) for s in supported):
        raise NotImplementedError(f"Return media type {value}")
    return value


def handle_query_params(
    url_class: Type["sdmx.rest.common.URL"],
    expr: str,
    values: Mapping,
    not_implemented=Collection[str],
) -> dict:
    """Extend :attr:`.query` with parts from `expr`, a " "-delimited string."""
    result = {}

    for p in map(url_class._all_parameters.__getitem__, expr.split()):
        assert isinstance(p, QueryParameter)

        # Store the value or the default
        result[p.name] = values.get(p.camelName, p.default)

        # Generate footer text for not implemented query parameters in `values`
        if result[p.name] != p.default:
            log.warning(
                "Ignored not implemented query parameter: "
                f"{p.camelName}={result[p.name]}"
            )

    return result


def not_implemented_path(defaults, **values):
    """Generate footer text for not implemented path parts in `values`."""
    for name, value in values.items():
        if value != defaults[name]:
            yield (
                f"Warning: ignored not implemented path part "
                f"{name}={value} != {repr(defaults[name])}"
            )
