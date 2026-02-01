"""
Add bio field to user table

Revision ID: b7a5d6c8e9fa
Revises: add_avatar_to_user
Create Date: 2025-12-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7a5d6c8e9fa'
down_revision = 'add_avatar_to_user'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bio', sa.Text(), nullable=True))

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('bio')
