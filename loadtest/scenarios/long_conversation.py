"""Long multi-turn chat: grows one session's history to stress the
full-history load / token-counting / compression path that single-turn runs
never reach. Run on its own (not in the default mix). See README.
"""

from __future__ import annotations

import os

from orbyte_client.chat_user import OrbyteChatUser
from orbyte_client.env import env_int


class LongConversationUser(OrbyteChatUser):
    abstract = False

    scenario_prefix: str = "longconv"
    mock_model: str | None = os.environ.get("ORBYTE_LONGCONV_MODEL")
    # Default 20 turns/session (base default is 1); ORBYTE_SESSION_TURNS overrides,
    # clamped to a minimum of 2 (a single turn defeats this scenario).
    max_session_turns: int = max(2, env_int("ORBYTE_SESSION_TURNS", 20))
