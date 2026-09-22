"""Initial schema with users and diagram_requests

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-22 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create diagram_requests table
    op.create_table(
        'diagram_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(1024), nullable=True),
        sa.Column('structured_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('complexity', sa.String(length=50), nullable=True),
        sa.Column('renderer', sa.String(length=50), nullable=True),
        sa.Column('diagram_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('output_path', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diagram_requests_id'), 'diagram_requests', ['id'], unique=False)
    op.create_index(op.f('ix_diagram_requests_user_id'), 'diagram_requests', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_diagram_requests_user_id'), table_name='diagram_requests')
    op.drop_index(op.f('ix_diagram_requests_id'), table_name='diagram_requests')
    op.drop_table('diagram_requests')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
