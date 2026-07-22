import pytest

from orbyte.auth.email_utils import build_user_email_invite
from orbyte.auth.email_utils import send_email
from orbyte.configs.constants import AuthType
from orbyte.configs.constants import ORBYTE_DEFAULT_APPLICATION_NAME
from orbyte.db.engine.sql_engine import SqlEngine
from orbyte.server.runtime.orbyte_runtime import OrbyteRuntime


@pytest.mark.skip(
    reason="This sends real emails, so only run when you really want to test this!"
)
def test_send_user_email_invite() -> None:
    SqlEngine.init_engine(pool_size=20, max_overflow=5)

    application_name = ORBYTE_DEFAULT_APPLICATION_NAME

    orbyte_file = OrbyteRuntime.get_emailable_logo()

    subject = f"Invitation to Join {application_name} Organization"

    FROM_EMAIL = "noreply@onyx.app"
    TO_EMAIL = "support@onyx.app"
    text_content, html_content = build_user_email_invite(
        FROM_EMAIL, TO_EMAIL, ORBYTE_DEFAULT_APPLICATION_NAME, AuthType.CLOUD
    )

    send_email(
        TO_EMAIL,
        subject,
        html_content,
        text_content,
        mail_from=FROM_EMAIL,
        inline_png=("logo.png", orbyte_file.data),
    )
