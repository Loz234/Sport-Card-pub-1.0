"""Create initial CardSignal schema

Revision ID: 20260813_0001
Revises:
Create Date: 2026-08-13 00:00:00.000000
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260813_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_sports_name", "sports", ["name"], unique=False)

    op.create_table(
        "grading_companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("abbreviation", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("abbreviation"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_grading_companies_name", "grading_companies", ["name"], unique=False)

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport_id", "name", name="uq_players_sport_name"),
    )
    op.create_index("ix_players_name", "players", ["name"], unique=False)
    op.create_index("ix_players_sport_id", "players", ["sport_id"], unique=False)

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("manufacturer", sa.String(length=120), nullable=False),
        sa.Column("set_name", sa.String(length=255), nullable=False),
        sa.Column("card_number", sa.String(length=50), nullable=False),
        sa.Column("is_rookie", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sport_id",
            "player_id",
            "year",
            "manufacturer",
            "set_name",
            "card_number",
            "is_rookie",
            name="uq_card_identity",
        ),
    )
    op.create_index("ix_cards_card_number", "cards", ["card_number"], unique=False)
    op.create_index("ix_cards_manufacturer", "cards", ["manufacturer"], unique=False)
    op.create_index("ix_cards_player_id", "cards", ["player_id"], unique=False)
    op.create_index("ix_cards_player_year", "cards", ["player_id", "year"], unique=False)
    op.create_index("ix_cards_set_name", "cards", ["set_name"], unique=False)
    op.create_index("ix_cards_sport_id", "cards", ["sport_id"], unique=False)
    op.create_index("ix_cards_year", "cards", ["year"], unique=False)

    op.create_table(
        "card_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("parallel", sa.String(length=120), nullable=True),
        sa.Column("serial_number", sa.String(length=50), nullable=True),
        sa.Column("is_autograph", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_memorabilia", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("grading_company_id", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grading_company_id"], ["grading_companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "card_id",
            "parallel",
            "serial_number",
            "is_autograph",
            "is_memorabilia",
            "grading_company_id",
            "grade",
            name="uq_card_variants_uniqueness",
        ),
    )
    op.create_index("ix_card_variants_card_id", "card_variants", ["card_id"], unique=False)
    op.create_index("ix_card_variants_card_parallel", "card_variants", ["card_id", "parallel"], unique=False)
    op.create_index("ix_card_variants_grading_company_id", "card_variants", ["grading_company_id"], unique=False)

    op.create_table(
        "historical_sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("sale_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sale_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marketplace", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default=sa.text("'USD'"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_historical_sales_card_date", "historical_sales", ["card_id", "sale_date"], unique=False)
    op.create_index("ix_historical_sales_card_id", "historical_sales", ["card_id"], unique=False)
    op.create_index("ix_historical_sales_marketplace", "historical_sales", ["marketplace"], unique=False)
    op.create_index("ix_historical_sales_sale_date", "historical_sales", ["sale_date"], unique=False)

    op.create_table(
        "market_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("listing_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("marketplace", sa.String(length=120), nullable=False),
        sa.Column("listing_url", sa.Text(), nullable=False),
        sa.Column("listing_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default=sa.text("'USD'"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_listings_card_active", "market_listings", ["card_id", "is_active"], unique=False)
    op.create_index("ix_market_listings_card_id", "market_listings", ["card_id"], unique=False)
    op.create_index("ix_market_listings_listing_date", "market_listings", ["listing_date"], unique=False)
    op.create_index("ix_market_listings_marketplace", "market_listings", ["marketplace"], unique=False)

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("average_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("min_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("max_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("listing_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("marketplace", sa.String(length=120), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default=sa.text("'USD'"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_snapshots_card_id", "market_snapshots", ["card_id"], unique=False)
    op.create_index("ix_market_snapshots_card_time", "market_snapshots", ["card_id", "snapshot_at"], unique=False)
    op.create_index("ix_market_snapshots_snapshot_at", "market_snapshots", ["snapshot_at"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("prediction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prediction_horizon_days", sa.Integer(), nullable=False),
        sa.Column("current_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("predicted_direction", sa.String(length=10), nullable=False),
        sa.Column("predicted_percentage_change", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_card_date_horizon", "predictions", ["card_id", "prediction_date", "prediction_horizon_days"], unique=False)
    op.create_index("ix_predictions_card_id", "predictions", ["card_id"], unique=False)
    op.create_index("ix_predictions_model_version", "predictions", ["model_version"], unique=False)
    op.create_index("ix_predictions_prediction_date", "predictions", ["prediction_date"], unique=False)
    op.create_index("ix_predictions_prediction_horizon_days", "predictions", ["prediction_horizon_days"], unique=False)

    op.create_table(
        "watchlists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("watcher_id", sa.String(length=120), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("watcher_id", "card_id", name="uq_watchlists_watcher_card"),
    )
    op.create_index("ix_watchlists_card_id", "watchlists", ["card_id"], unique=False)
    op.create_index("ix_watchlists_created_at", "watchlists", ["created_at"], unique=False)
    op.create_index("ix_watchlists_watcher_id", "watchlists", ["watcher_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_watchlists_watcher_id", table_name="watchlists")
    op.drop_index("ix_watchlists_created_at", table_name="watchlists")
    op.drop_index("ix_watchlists_card_id", table_name="watchlists")
    op.drop_table("watchlists")

    op.drop_index("ix_predictions_prediction_horizon_days", table_name="predictions")
    op.drop_index("ix_predictions_prediction_date", table_name="predictions")
    op.drop_index("ix_predictions_model_version", table_name="predictions")
    op.drop_index("ix_predictions_card_id", table_name="predictions")
    op.drop_index("ix_predictions_card_date_horizon", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index("ix_market_snapshots_snapshot_at", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_card_time", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_card_id", table_name="market_snapshots")
    op.drop_table("market_snapshots")

    op.drop_index("ix_market_listings_marketplace", table_name="market_listings")
    op.drop_index("ix_market_listings_listing_date", table_name="market_listings")
    op.drop_index("ix_market_listings_card_id", table_name="market_listings")
    op.drop_index("ix_market_listings_card_active", table_name="market_listings")
    op.drop_table("market_listings")

    op.drop_index("ix_historical_sales_sale_date", table_name="historical_sales")
    op.drop_index("ix_historical_sales_marketplace", table_name="historical_sales")
    op.drop_index("ix_historical_sales_card_id", table_name="historical_sales")
    op.drop_index("ix_historical_sales_card_date", table_name="historical_sales")
    op.drop_table("historical_sales")

    op.drop_index("ix_card_variants_grading_company_id", table_name="card_variants")
    op.drop_index("ix_card_variants_card_parallel", table_name="card_variants")
    op.drop_index("ix_card_variants_card_id", table_name="card_variants")
    op.drop_table("card_variants")

    op.drop_index("ix_cards_year", table_name="cards")
    op.drop_index("ix_cards_sport_id", table_name="cards")
    op.drop_index("ix_cards_set_name", table_name="cards")
    op.drop_index("ix_cards_player_year", table_name="cards")
    op.drop_index("ix_cards_player_id", table_name="cards")
    op.drop_index("ix_cards_manufacturer", table_name="cards")
    op.drop_index("ix_cards_card_number", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ix_players_sport_id", table_name="players")
    op.drop_index("ix_players_name", table_name="players")
    op.drop_table("players")

    op.drop_index("ix_grading_companies_name", table_name="grading_companies")
    op.drop_table("grading_companies")

    op.drop_index("ix_sports_name", table_name="sports")
    op.drop_table("sports")
