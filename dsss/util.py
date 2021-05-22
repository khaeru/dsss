from datetime import datetime

import sdmx


def prepare_message(msg, footer_info):
    # Set the prepared time
    msg.header.prepared = datetime.now()

    if msg.footer is None:
        msg.footer = sdmx.message.Footer()

    msg.footer.text.append(", ".join(map(repr, footer_info)))
