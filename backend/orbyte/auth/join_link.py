"""Group join link token generation and validation."""

import hashlib
import secrets

JOIN_LINK_PREFIX = "orbyte_join_"
JOIN_LINK_LENGTH = 48


def generate_join_link_token() -> str:
    """Generate a cryptographically secure join-link token."""
    return JOIN_LINK_PREFIX + secrets.token_urlsafe(JOIN_LINK_LENGTH)


def hash_join_link_token(token: str) -> str:
    """Hash a join-link token using SHA256 (no salt needed due to cryptographic randomness)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
