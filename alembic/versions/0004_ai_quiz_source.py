"""add question source metadata for AI-generated quizzes"""
from alembic import op
import sqlalchemy as sa

revision = "0004_ai_quiz_source"
down_revision = "0003_v34_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"))
    op.add_column("questions", sa.Column("ai_batch_id", sa.String(length=64), nullable=True))
    op.create_index("ix_questions_source", "questions", ["source"], unique=False)
    op.create_index("ix_questions_ai_batch_id", "questions", ["ai_batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_questions_ai_batch_id", table_name="questions")
    op.drop_index("ix_questions_source", table_name="questions")
    op.drop_column("questions", "ai_batch_id")
    op.drop_column("questions", "source")
