-- Phase D: per-company signature library. Same "one row per asset,
-- company-scoped, RLS-isolated" pattern as quotation_templates, but
-- multiple signatures are allowed per company (no unique(company_id)) -
-- a company can have several authorized signatories, one of which is
-- picked per quotation at generation time.
create table signatures (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    name text not null,
    designation text not null default '',
    image_storage_path text not null,
    active boolean not null default true,
    created_by uuid not null references users(id),
    created_at timestamptz not null default now()
);

alter table signatures enable row level security;
alter table signatures force row level security;
create policy company_isolation on signatures
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );
