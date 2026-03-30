"""initial schema

Revision ID: 3335da39959a
Revises:
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3335da39959a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_chat_id", sa.String(50), nullable=False),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("notifications_sent", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_users_telegram", "users", ["telegram_chat_id"], unique=True)

    # --- properties ---
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # prices
        sa.Column("price_uf", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_clp", sa.Integer(), nullable=True),
        sa.Column("price_m2_uf", sa.Numeric(8, 2), nullable=True),
        # area
        sa.Column("m2_total", sa.Numeric(8, 2), nullable=True),
        sa.Column("m2_util", sa.Numeric(8, 2), nullable=True),
        # features
        sa.Column("bedrooms", sa.SmallInteger(), nullable=True),
        sa.Column("bathrooms", sa.SmallInteger(), nullable=True),
        sa.Column("floor", sa.SmallInteger(), nullable=True),
        sa.Column("has_parking", sa.Boolean(), nullable=True),
        sa.Column("has_bodega", sa.Boolean(), nullable=True),
        sa.Column("building_year", sa.SmallInteger(), nullable=True),
        # location
        sa.Column("commune", sa.String(100), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        # json
        sa.Column("images", postgresql.JSON(), nullable=True),
        sa.Column("raw_data", postgresql.JSON(), nullable=True),
        # opportunity
        sa.Column("is_opportunity", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("opportunity_score", sa.SmallInteger(), nullable=True),
        sa.Column("has_urgency_keyword", sa.Boolean(), server_default=sa.text("false")),
        # state
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        # timestamps
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_properties_source_id", "properties", ["source", "source_id"], unique=True
    )
    op.create_index("idx_properties_commune", "properties", ["commune"])
    op.create_index("idx_properties_price_uf", "properties", ["price_uf"])
    op.create_index(
        "idx_properties_opportunity",
        "properties",
        ["is_opportunity"],
        postgresql_where=sa.text("is_opportunity = true"),
    )
    op.create_index(
        "idx_properties_active",
        "properties",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # --- alerts ---
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("min_price_uf", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price_uf", sa.Numeric(10, 2), nullable=True),
        sa.Column("target_communes", postgresql.JSON(), nullable=True),
        sa.Column("min_bedrooms", sa.SmallInteger(), nullable=True),
        sa.Column("max_bedrooms", sa.SmallInteger(), nullable=True),
        sa.Column("min_score", sa.SmallInteger(), server_default=sa.text("70")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- notification_log ---
    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id"),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("channel", sa.String(20), server_default=sa.text("'telegram'")),
        sa.Column("status", sa.String(20), server_default=sa.text("'sent'")),
    )
    op.create_index(
        "idx_notif_user_prop",
        "notification_log",
        ["user_id", "property_id"],
        unique=True,
    )
    op.create_index(
        "idx_notif_user_sent", "notification_log", ["user_id", "sent_at"]
    )

    # --- feedbacks ---
    op.create_table(
        "feedbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id"),
            nullable=False,
        ),
        sa.Column("is_good", sa.Boolean(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_feedback_user_prop",
        "feedbacks",
        ["user_id", "property_id"],
        unique=True,
    )

    # --- market_averages ---
    op.create_table(
        "market_averages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("commune", sa.String(100), nullable=False),
        sa.Column("bedrooms", sa.SmallInteger(), nullable=False),
        sa.Column("avg_price_m2_uf", sa.Numeric(8, 2), nullable=False),
        sa.Column("median_price_m2_uf", sa.Numeric(8, 2), nullable=True),
        sa.Column("min_price_m2_uf", sa.Numeric(8, 2), nullable=True),
        sa.Column("max_price_m2_uf", sa.Numeric(8, 2), nullable=True),
        sa.Column("sample_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("std_deviation", sa.Numeric(8, 2), nullable=True),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_market_commune_beds",
        "market_averages",
        ["commune", "bedrooms"],
        unique=True,
    )

    # --- rent_averages ---
    op.create_table(
        "rent_averages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("commune", sa.String(100), nullable=False),
        sa.Column("bedrooms", sa.SmallInteger(), nullable=False),
        sa.Column("avg_rent_uf", sa.Numeric(8, 2), nullable=False),
        sa.Column("median_rent_uf", sa.Numeric(8, 2), nullable=True),
        sa.Column("min_rent_uf", sa.Numeric(8, 2), nullable=True),
        sa.Column("max_rent_uf", sa.Numeric(8, 2), nullable=True),
        sa.Column("sample_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_rent_commune_beds",
        "rent_averages",
        ["commune", "bedrooms"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("rent_averages")
    op.drop_table("market_averages")
    op.drop_table("feedbacks")
    op.drop_table("notification_log")
    op.drop_table("alerts")
    op.drop_table("properties")
    op.drop_table("users")
