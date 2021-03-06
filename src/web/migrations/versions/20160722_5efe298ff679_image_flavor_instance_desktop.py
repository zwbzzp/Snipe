""""image_flavor_instance_desktop"

Revision ID: 5efe298ff679
Revises: b7db3a535cb6
Create Date: 2016-07-22 16:54:50.215460

"""

# revision identifiers, used by Alembic.
revision = '5efe298ff679'
down_revision = 'b7db3a535cb6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('instances')
    op.add_column('desktops', sa.Column('flavor_ref', sa.String(length=64), nullable=True))
    op.add_column('desktops', sa.Column('image_ref', sa.String(length=64), nullable=True))
    op.add_column('flavors', sa.Column('description', sa.String(length=64), nullable=True))
    op.add_column('images', sa.Column('name', sa.String(length=64), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('images', 'name')
    op.drop_column('flavors', 'description')
    op.drop_column('desktops', 'image_ref')
    op.drop_column('desktops', 'flavor_ref')
    op.create_table('instances',
    sa.Column('id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column('created_at', mysql.DATETIME(), nullable=True),
    sa.Column('updated_at', mysql.DATETIME(), nullable=True),
    sa.Column('vmid', mysql.VARCHAR(length=64), nullable=True),
    sa.Column('image', mysql.VARCHAR(length=64), nullable=True),
    sa.Column('flavor', mysql.VARCHAR(length=64), nullable=True),
    sa.Column('name', mysql.VARCHAR(length=64), nullable=True),
    sa.Column('description', mysql.VARCHAR(length=255), nullable=True),
    sa.Column('status', mysql.VARCHAR(length=64), nullable=True),
    sa.Column('ip', mysql.VARCHAR(length=64), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='utf8',
    mysql_engine='InnoDB'
    )
    ### end Alembic commands ###
