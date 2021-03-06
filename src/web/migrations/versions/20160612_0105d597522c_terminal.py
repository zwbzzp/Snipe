""""terminal"

Revision ID: 0105d597522c
Revises: 30a6e384c345
Create Date: 2016-06-12 18:27:47.483059

"""

# revision identifiers, used by Alembic.
revision = '0105d597522c'
down_revision = '30a6e384c345'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('terminal_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('password', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_terminal_users_username'), 'terminal_users', ['username'], unique=True)
    op.create_table('terminals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('mac_address', sa.String(length=64), nullable=False),
    sa.Column('seat_number', sa.String(length=64), nullable=False),
    sa.Column('description', sa.String(length=1024), nullable=True),
    sa.Column('info', sa.String(length=1024), nullable=True),
    sa.Column('state', sa.String(length=64), nullable=True),
    sa.Column('terminal_user_id', sa.Integer(), nullable=True),
    sa.Column('place_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.ForeignKeyConstraint(['terminal_user_id'], ['terminal_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_terminals_state'), 'terminals', ['state'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_terminals_state'), table_name='terminals')
    op.drop_table('terminals')
    op.drop_index(op.f('ix_terminal_users_username'), table_name='terminal_users')
    op.drop_table('terminal_users')
    ### end Alembic commands ###
