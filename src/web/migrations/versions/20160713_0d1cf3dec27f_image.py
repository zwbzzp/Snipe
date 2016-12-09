""""image"

Revision ID: 0d1cf3dec27f
Revises: a96d51e1001f
Create Date: 2016-07-13 14:29:09.538218

"""

# revision identifiers, used by Alembic.
revision = '0d1cf3dec27f'
down_revision = 'a96d51e1001f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('images', sa.Column('description', sa.String(length=256), nullable=True))
    op.add_column('images', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'images', 'users', ['owner_id'], ['id'])
    op.drop_column('images', 'name')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('images', sa.Column('name', mysql.VARCHAR(length=64), nullable=True))
    op.drop_constraint(None, 'images', type_='foreignkey')
    op.drop_column('images', 'owner_id')
    op.drop_column('images', 'description')
    ### end Alembic commands ###
