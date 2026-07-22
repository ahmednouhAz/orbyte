"""Unit tests for the hooks feature gate."""

from unittest.mock import patch

import pytest

from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError
from orbyte.hooks.api_dependencies import require_hook_enabled


class TestRequireHookEnabled:
    def test_raises_when_multi_tenant(self) -> None:
        with patch("orbyte.hooks.api_dependencies.MULTI_TENANT", True):
            with pytest.raises(OrbyteError) as exc_info:
                require_hook_enabled()
        assert exc_info.value.error_code is OrbyteErrorCode.SINGLE_TENANT_ONLY
        assert exc_info.value.status_code == 403
        assert "multi-tenant" in exc_info.value.detail

    def test_passes_when_single_tenant(self) -> None:
        with patch("orbyte.hooks.api_dependencies.MULTI_TENANT", False):
            require_hook_enabled()  # must not raise
