-- Phase C: per-company quotation template (replaces the static
-- app/quotation_templates/ file with a Storage-backed upload, same "one
-- active version, upsert on replace" pattern as master_excel) and logo
-- (simple enough to be columns on companies rather than its own table).
create table quotation_templates (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    storage_path text not null,
    original_filename text not null,
    uploaded_by uuid not null references users(id),
    uploaded_at timestamptz not null default now(),
    file_size bigint not null,
    unique (company_id)
);

alter table quotation_templates enable row level security;
alter table quotation_templates force row level security;
create policy company_isolation on quotation_templates
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );

alter table companies add column logo_storage_path text;
alter table companies add column logo_uploaded_at timestamptz;
alter table companies add column logo_uploaded_by uuid references users(id);
