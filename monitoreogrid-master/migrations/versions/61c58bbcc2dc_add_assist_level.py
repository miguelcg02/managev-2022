"""add assist level

Revision ID: 61c58bbcc2dc
Revises: 66142c6cd095
Create Date: 2021-05-21 08:15:23.030347

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "61c58bbcc2dc"
down_revision = "66142c6cd095"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("operation", sa.Column("assist_level", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("operation", "assist_level")
    # ### end Alembic commands ###
