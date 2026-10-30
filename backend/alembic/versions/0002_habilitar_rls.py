"""habilitar RLS en todas las tablas del schema public

Supabase expone automáticamente el schema public por su API REST (PostgREST). Con RLS activado
y sin políticas, esa API no puede leer ni escribir nada; la aplicación accede con la conexión
directa a Postgres (rol dueño de las tablas, que no está sujeto a RLS).

Las tablas que se creen en migraciones futuras deben repetir ALTER TABLE ... ENABLE ROW LEVEL SECURITY.
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', r.tablename);
            END LOOP;
        END $$;
        """
    )
