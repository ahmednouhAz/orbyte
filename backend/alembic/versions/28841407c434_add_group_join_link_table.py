"""add_group_join_link_table

Revision ID: 28841407c434
Revises: b7e9a3c1d2f4
Create Date: 2026-07-20 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "28841407c434"
down_revision = "b7e9a3c1d2f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_join_link",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_group_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("is_reusable", sa.Boolean(), nullable=False),
        sa.Column(
            "use_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_group_id"],
            ["user_group.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )

    op.create_index(
        "ix_group_join_link_user_group_id",
        "group_join_link",
        ["user_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_group_join_link_user_group_id", table_name="group_join_link")
    op.drop_table("group_join_link")
