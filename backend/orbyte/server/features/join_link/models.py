import datetime

from pydantic import BaseModel

from orbyte.db.models import GroupJoinLink


class JoinLinkCreate(BaseModel):
    is_reusable: bool
    expires_in_hours: int | None = None


class JoinLinkCreateResponse(BaseModel):
    id: int
    token: str
    is_reusable: bool
    expires_at: datetime.datetime | None

    @classmethod
    def from_model(cls, link: GroupJoinLink, token: str) -> "JoinLinkCreateResponse":
        return cls(
            id=link.id,
            token=token,
            is_reusable=link.is_reusable,
            expires_at=link.expires_at,
        )


class JoinLinkSnapshot(BaseModel):
    id: int
    is_reusable: bool
    use_count: int
    expires_at: datetime.datetime | None
    revoked_at: datetime.datetime | None
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, link: GroupJoinLink) -> "JoinLinkSnapshot":
        return cls(
            id=link.id,
            is_reusable=link.is_reusable,
            use_count=link.use_count,
            expires_at=link.expires_at,
            revoked_at=link.revoked_at,
            created_at=link.created_at,
        )


class JoinLinkLookupResponse(BaseModel):
    valid: bool
    group_name: str | None = None


class JoinLinkRedeemRequest(BaseModel):
    email: str
    password: str


class JoinLinkRedeemResponse(BaseModel):
    id: str
    email: str
