"""
Add avatar field to user table

Revision ID: add_avatar_to_user
Revises: df4243ffbb73
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_avatar_to_user'
down_revision = 'df4243ffbb73'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('avatar', sa.String(length=256), nullable=True))

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('avatar')
