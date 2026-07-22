"""Client drops the stream mid-turn (default: after the first answer token)
to exercise server-side disconnect cleanup (held transactions/connections/
buffers). Recorded as `<prefix>:disconnected`, not a failure. Run on its own
(not in the default mix). See README.
"""

from __future__ import annotations

import os

from orbyte_client.chat_user import OrbyteChatUser


class DisconnectUser(OrbyteChatUser):
    abstract = False

    scenario_prefix: str = "disconnect"
    disconnect_after_milestone: str | None = os.environ.get(
        "ORBYTE_DISCONNECT_AFTER", "first_answer_token"
    )
