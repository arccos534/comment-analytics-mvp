"""initial schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260312_0001"
down_revision = None
branch_labels = None
depends_on = None


platform_enum = postgresql.ENUM("telegram", "vk", name="platform_enum", create_type=False)
source_type_enum = postgresql.ENUM("channel", "community", "post", name="source_type_enum", create_type=False)
source_status_enum = postgresql.ENUM(
    "pending", "valid", "invalid", "indexing", "ready", "failed", name="source_status_enum", create_type=False
)
analysis_run_status_enum = postgresql.ENUM(
    "pending", "running", "completed", "failed", name="analysis_run_status_enum", create_type=False
)
sentiment_enum = postgresql.ENUM("positive", "negative", "neutral", name="sentiment_enum", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    platform_enum.create(bind, checkfirst=True)
    source_type_enum.create(bind, checkfirst=True)
    source_status_enum.create(bind, checkfirst=True)
    analysis_run_status_enum.create(bind, checkfirst=True)
    sentiment_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "projects",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_projects_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )

    op.create_table(
        "sources",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", platform_enum, nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("external_source_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", source_status_enum, nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_sources_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("project_id", "source_url", name="uq_sources_project_id_source_url"),
    )
    op.create_index("ix_sources_project_id", "sources", ["project_id"], unique=False)

    op.create_table(
        "posts",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_post_id", sa.String(length=255), nullable=False),
        sa.Column("post_url", sa.Text(), nullable=False),
        sa.Column("post_text", sa.Text(), nullable=True),
        sa.Column("post_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("likes_count", sa.Integer(), nullable=False),
        sa.Column("views_count", sa.Integer(), nullable=False),
        sa.Column("comments_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name="fk_posts_source_id_sources"),
        sa.PrimaryKeyConstraint("id", name="pk_posts"),
        sa.UniqueConstraint("source_id", "external_post_id", name="uq_posts_source_id_external_post_id"),
    )
    op.create_index("ix_posts_source_id_post_date", "posts", ["source_id", "post_date"], unique=False)

    op.create_table(
        "comments",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_comment_id", sa.String(length=255), nullable=False),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_external_id_hash", sa.String(length=255), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("likes_count", sa.Integer(), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], name="fk_comments_parent_comment_id_comments"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], name="fk_comments_post_id_posts"),
        sa.PrimaryKeyConstraint("id", name="pk_comments"),
        sa.UniqueConstraint("post_id", "external_comment_id", name="uq_comments_post_id_external_comment_id"),
    )
    op.create_index("ix_comments_post_id_created_at", "comments", ["post_id", "created_at"], unique=False)

    op.create_table(
        "analysis_runs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("theme", sa.Text(), nullable=True),
        sa.Column("keywords_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("period_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", analysis_run_status_enum, nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_analysis_runs_project_id_projects"),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_runs"),
    )
    op.create_index("ix_analysis_runs_project_id_created_at", "analysis_runs", ["project_id", "created_at"], unique=False)

    op.create_table(
        "comment_analysis",
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sentiment", sentiment_enum, nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("topics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("keywords_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("toxicity_score", sa.Float(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], name="fk_comment_analysis_comment_id_comments"),
        sa.PrimaryKeyConstraint("id", name="pk_comment_analysis"),
        sa.UniqueConstraint("comment_id", name="uq_comment_analysis_comment_id"),
    )
    op.create_index("ix_comment_analysis_sentiment", "comment_analysis", ["sentiment"], unique=False)

    op.create_table(
        "report_snapshots",
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], name="fk_report_snapshots_analysis_run_id_analysis_runs"),
        sa.PrimaryKeyConstraint("id", name="pk_report_snapshots"),
    )


def downgrade() -> None:
    op.drop_table("report_snapshots")
    op.drop_index("ix_comment_analysis_sentiment", table_name="comment_analysis")
    op.drop_table("comment_analysis")
    op.drop_index("ix_analysis_runs_project_id_created_at", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index("ix_comments_post_id_created_at", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_posts_source_id_post_date", table_name="posts")
    op.drop_table("posts")
    op.drop_index("ix_sources_project_id", table_name="sources")
    op.drop_table("sources")
    op.drop_table("projects")
    op.drop_table("users")

    bind = op.get_bind()
    sentiment_enum.drop(bind, checkfirst=True)
    analysis_run_status_enum.drop(bind, checkfirst=True)
    source_status_enum.drop(bind, checkfirst=True)
    source_type_enum.drop(bind, checkfirst=True)
    platform_enum.drop(bind, checkfirst=True)
