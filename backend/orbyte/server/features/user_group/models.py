from uuid import UUID

from pydantic import BaseModel

from orbyte.db.models import UserGroup as UserGroupDBModel
from orbyte.server.documents.models import CCPairSummary
from orbyte.server.features.document_set.models import DocumentSetSummary
from orbyte.server.features.persona.models import PersonaSnapshot


class UserGroupCreate(BaseModel):
    name: str
    user_ids: list[UUID] = []
    cc_pair_ids: list[int] = []


class UserGroupUpdate(BaseModel):
    user_ids: list[UUID] = []
    cc_pair_ids: list[int] = []
    curator_ids: list[UUID] = []


class UserGroupRename(BaseModel):
    id: int
    name: str


class AddUsersToUserGroupRequest(BaseModel):
    user_ids: list[UUID]


class UpdateGroupAgentsRequest(BaseModel):
    added_agent_ids: list[int] = []
    removed_agent_ids: list[int] = []


class GroupMemberSnapshot(BaseModel):
    id: UUID
    email: str
    is_active: bool


class MinimalUserGroupSnapshot(BaseModel):
    id: int
    name: str

    @classmethod
    def from_model(cls, group: UserGroupDBModel) -> "MinimalUserGroupSnapshot":
        return cls(id=group.id, name=group.name)


class UserGroupSnapshot(BaseModel):
    id: int
    name: str
    users: list[GroupMemberSnapshot]
    curator_ids: list[UUID]
    cc_pairs: list[CCPairSummary]
    document_sets: list[DocumentSetSummary]
    personas: list[PersonaSnapshot]
    is_up_to_date: bool
    is_up_for_deletion: bool
    is_default: bool

    @classmethod
    def from_model(cls, group: UserGroupDBModel) -> "UserGroupSnapshot":
        curator_ids = [
            rel.user_id
            for rel in group.user_group_relationships
            if rel.is_curator and rel.user_id is not None
        ]
        return cls(
            id=group.id,
            name=group.name,
            users=[
                GroupMemberSnapshot(
                    id=user.id, email=user.email, is_active=user.is_active
                )
                for user in group.users
            ],
            curator_ids=curator_ids,
            cc_pairs=[
                CCPairSummary(
                    id=cc_pair.id,
                    name=cc_pair.name,
                    source=cc_pair.connector.source,
                    access_type=cc_pair.access_type,
                )
                for cc_pair in group.cc_pairs
            ],
            document_sets=[
                DocumentSetSummary.from_model(document_set)
                for document_set in group.document_sets
            ],
            personas=[PersonaSnapshot.from_model(persona) for persona in group.personas],
            is_up_to_date=group.is_up_to_date,
            is_up_for_deletion=group.is_up_for_deletion,
            is_default=group.is_default,
        )
