from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from orbyte.auth.join_link import generate_join_link_token
from orbyte.auth.join_link import hash_join_link_token
from orbyte.db.models import GroupJoinLink


def create_join_link(
    db_session: Session,
    user_group_id: int,
    created_by: UUID | None,
    is_reusable: bool,
    expires_at: datetime | None,
) -> tuple[GroupJoinLink, str]:
    """Create a new join link. Returns (db_record, raw_token) — the raw token
    is never stored and cannot be recovered later, only the hash is kept."""
    token = generate_join_link_token()
    link = GroupJoinLink(
        token_hash=hash_join_link_token(token),
        user_group_id=user_group_id,
        created_by=created_by,
        is_reusable=is_reusable,
        expires_at=expires_at,
    )
    db_session.add(link)
    db_session.commit()
    return link, token


def fetch_join_links_for_group(
    db_session: Session, user_group_id: int
) -> Sequence[GroupJoinLink]:
    return db_session.scalars(
        select(GroupJoinLink)
        .where(GroupJoinLink.user_group_id == user_group_id)
        .order_by(GroupJoinLink.created_at.desc())
    ).all()


def fetch_join_link_by_id(
    db_session: Session, link_id: int
) -> GroupJoinLink | None:
    return db_session.scalar(
        select(GroupJoinLink).where(GroupJoinLink.id == link_id)
    )


def revoke_join_link(db_session: Session, link: GroupJoinLink) -> None:
    link.revoked_at = datetime.now(timezone.utc)
    db_session.commit()


def resolve_join_link(db_session: Session, token: str) -> GroupJoinLink | None:
    """Resolve a raw token to its link, or None if it doesn't exist, is
    revoked, is expired, or (being single-use) has already been redeemed."""
    link = db_session.scalar(
        select(GroupJoinLink).where(
            GroupJoinLink.token_hash == hash_join_link_token(token)
        )
    )
    if link is None:
        return None
    if link.revoked_at is not None:
        return None
    if link.expires_at is not None and link.expires_at <= datetime.now(timezone.utc):
        return None
    if not link.is_reusable and link.use_count >= 1:
        return None
    return link


def record_join_link_use__no_commit(link: GroupJoinLink) -> None:
    """NOTE: does not commit transaction, this must be done by the caller"""
    link.use_count += 1
