"""Unit tests for `OrbytePatResolver`.

Coverage: the host claim rule (incl. inert when `SANDBOX_API_SERVER_URL` is
unset), header rendering on both auth headers, and the fail-closed cases the
dispatcher maps to a 403. The encrypt/store/read round-trip against a real DB
is pinned in `tests/external_dependency_unit/sandbox_proxy/test_orbyte_pat_resolver.py`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from orbyte.auth.constants import API_KEY_HEADER_ALTERNATIVE_NAME
from orbyte.auth.constants import API_KEY_HEADER_NAME
from orbyte.sandbox_proxy.credential_injection import CredentialUnavailableError
from orbyte.sandbox_proxy.credential_injection import InjectionContext
from orbyte.sandbox_proxy.resolvers import orbyte_pat
from orbyte.sandbox_proxy.resolvers.orbyte_pat import OrbytePatResolver
from tests.unit.sandbox_proxy.conftest import make_flow
from tests.unit.sandbox_proxy.conftest import make_resolved_sandbox

_API_URL = "https://api.orbyte.example.com"
_API_HOST = "api.orbyte.example.com"


class _FakeEncrypted:
    def __init__(
        self, *, value: str | None = None, exc: Exception | None = None
    ) -> None:
        self._value = value
        self._exc = exc

    def get_value(self, apply_mask: bool) -> str | None:  # noqa: ARG002
        if self._exc is not None:
            raise self._exc
        return self._value


class _FakeSandbox:
    def __init__(self, encrypted_pat: _FakeEncrypted | None) -> None:
        self.encrypted_pat = encrypted_pat


def _noop_db_factory() -> Any:
    @contextmanager
    def factory(tenant_id: str) -> Iterator[Any]:  # noqa: ARG001
        yield MagicMock()

    return factory


@pytest.fixture(autouse=True)
def _patch_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """The resolver opens its own tenant session via `get_session_with_tenant`;
    yield a dummy so the patched DB-access functions receive it."""
    monkeypatch.setattr(orbyte_pat, "get_session_with_tenant", _noop_db_factory())


def _ctx() -> InjectionContext:
    return InjectionContext(
        sandbox=make_resolved_sandbox(tenant_id="tenant-7"), matched_actions=None
    )


@pytest.fixture
def resolver(monkeypatch: pytest.MonkeyPatch) -> OrbytePatResolver:
    # __init__ captures the API host, so the patch must precede construction.
    monkeypatch.setattr(orbyte_pat, "SANDBOX_API_SERVER_URL", _API_URL)
    return OrbytePatResolver()


def test_claims_requires_matching_host_and_port(resolver: OrbytePatResolver) -> None:
    # _API_URL is https with no explicit port, so the effective port is 443.
    assert resolver.claims(make_flow(host=_API_HOST, port=443).request, _ctx()) is True
    assert (
        resolver.claims(make_flow(host=_API_HOST.upper(), port=443).request, _ctx())
        is True
    )
    assert (
        resolver.claims(make_flow(host=_API_HOST, port=8080).request, _ctx()) is False
    )
    assert (
        resolver.claims(make_flow(host="api.slack.com", port=443).request, _ctx())
        is False
    )


def test_claims_matches_explicit_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orbyte_pat, "SANDBOX_API_SERVER_URL", "http://internal:8080")
    resolver = OrbytePatResolver()
    assert (
        resolver.claims(make_flow(host="internal", port=8080).request, _ctx()) is True
    )
    assert (
        resolver.claims(make_flow(host="internal", port=443).request, _ctx()) is False
    )


def test_inert_when_api_url_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orbyte_pat, "SANDBOX_API_SERVER_URL", "")
    assert (
        OrbytePatResolver().claims(make_flow(host=_API_HOST, port=443).request, _ctx())
        is False
    )


def test_resolve_renders_pat_on_both_auth_headers(
    resolver: OrbytePatResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        orbyte_pat,
        "get_sandbox_by_id",
        lambda *_: _FakeSandbox(_FakeEncrypted(value="orbyte_pat_t.secret")),
    )
    headers = resolver.resolve(make_flow(host=_API_HOST).request, _ctx())
    assert headers == {
        API_KEY_HEADER_NAME: "Bearer orbyte_pat_t.secret",
        API_KEY_HEADER_ALTERNATIVE_NAME: "Bearer orbyte_pat_t.secret",
    }


def test_resolve_raises_when_sandbox_missing(
    resolver: OrbytePatResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(orbyte_pat, "get_sandbox_by_id", lambda *_: None)
    with pytest.raises(CredentialUnavailableError):
        resolver.resolve(make_flow(host=_API_HOST).request, _ctx())


def test_resolve_raises_when_pat_unset(
    resolver: OrbytePatResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(orbyte_pat, "get_sandbox_by_id", lambda *_: _FakeSandbox(None))
    with pytest.raises(CredentialUnavailableError):
        resolver.resolve(make_flow(host=_API_HOST).request, _ctx())


def test_resolve_raises_when_decrypt_fails(
    resolver: OrbytePatResolver, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        orbyte_pat,
        "get_sandbox_by_id",
        lambda *_: _FakeSandbox(_FakeEncrypted(exc=ValueError("boom"))),
    )
    with pytest.raises(CredentialUnavailableError):
        resolver.resolve(make_flow(host=_API_HOST).request, _ctx())
