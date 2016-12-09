""""hostinfo_03"

Revision ID: 3d3b965e7856
Revises: 2d274cd8b63b
Create Date: 2016-08-18 17:23:15.424192

"""

# revision identifiers, used by Alembic.
revision = '3d3b965e7856'
down_revision = '2d274cd8b63b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('hostinfo', sa.Column('auto_evacuation', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('hostinfo', 'auto_evacuation')
    ### end Alembic commands ###