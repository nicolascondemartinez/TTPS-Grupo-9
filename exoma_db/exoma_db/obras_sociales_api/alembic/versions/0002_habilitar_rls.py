"""habilitar RLS en el schema obras_sociales (sin políticas: solo accede la conexión directa de la app)"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_SQL = """
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'obras_sociales' LOOP
        EXECUTE format('ALTER TABLE obras_sociales.%I {accion} ROW LEVEL SECURITY', r.tablename);
    END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(_SQL.format(accion="ENABLE"))


def downgrade() -> None:
    op.execute(_SQL.format(accion="DISABLE"))
