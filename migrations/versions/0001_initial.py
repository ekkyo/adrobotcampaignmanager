"""Initial campaign and offer tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    existing = set(inspect(op.get_bind()).get_table_names())
    if "campaigns" not in existing:
        op.create_table("campaigns",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("keitaro_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("country", sa.String(length=2), nullable=False),
            sa.UniqueConstraint("keitaro_id", name="uq_campaigns_keitaro_id"))
    if "campaign_offers" not in existing:
        op.create_table("campaign_offers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
            sa.Column("offer_id", sa.Integer(), nullable=False))

def downgrade():
    op.drop_table("campaign_offers")
    op.drop_table("campaigns")
