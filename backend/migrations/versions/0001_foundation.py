r"""迁移链第 1 步：extensions / schema / helper（12 步顺序第①步）。

- 建立 `platform` schema：所有业务对象统一放这里（04 基线 6.x）；
- 启用 `vector` 扩展（pgvector）：sources_context 小规模精确检索用；
- 角色/账户分离、identity/project、run 核心表族等在后续迁移按 04 物理设计落地。

真实执行的唯一口径：运行 `uv run alembic upgrade head` 后由 `alembic current` 与
`\dx` 核对，不以「文件已写」冒充迁移已生效。
"""
from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS platform")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "COMMENT ON SCHEMA platform IS 'ai-native platform 业务对象统一 schema'"
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS platform CASCADE")
    op.execute("DROP EXTENSION IF EXISTS vector")