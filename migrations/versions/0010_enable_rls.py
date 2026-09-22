"""enable row level security on all public tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-17

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Blocks Supabase's PostgREST layer (the anon/authenticated roles) from
    # reading or writing these tables directly -- the app's only intended
    # access path is the FastAPI backend's own API-key check, never
    # Supabase's public data API. The backend connects as `postgres`
    # (confirmed via DATABASE_URL and a live `pg_roles` check); that role
    # already has rolbypassrls = true, so it bypasses RLS unconditionally
    # regardless of policy content -- the explicit policies below are
    # defense-in-depth on top of that confirmed bypass, not a substitute
    # for it, in case that role attribute is ever revoked later.
    op.execute("ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY backend_full_access ON public.incidents "
        "FOR ALL TO postgres USING (true) WITH CHECK (true)"
    )

    op.execute("ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY backend_full_access ON public.documents "
        "FOR ALL TO postgres USING (true) WITH CHECK (true)"
    )

    op.execute("ALTER TABLE public.daily_spend ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY backend_full_access ON public.daily_spend "
        "FOR ALL TO postgres USING (true) WITH CHECK (true)"
    )

    op.execute("ALTER TABLE public.daily_injections ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY backend_full_access ON public.daily_injections "
        "FOR ALL TO postgres USING (true) WITH CHECK (true)"
    )

    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY backend_full_access ON public.alembic_version "
        "FOR ALL TO postgres USING (true) WITH CHECK (true)"
    )


def downgrade() -> None:
    op.execute("DROP POLICY backend_full_access ON public.alembic_version")
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY backend_full_access ON public.daily_injections")
    op.execute("ALTER TABLE public.daily_injections DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY backend_full_access ON public.daily_spend")
    op.execute("ALTER TABLE public.daily_spend DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY backend_full_access ON public.documents")
    op.execute("ALTER TABLE public.documents DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY backend_full_access ON public.incidents")
    op.execute("ALTER TABLE public.incidents DISABLE ROW LEVEL SECURITY")
