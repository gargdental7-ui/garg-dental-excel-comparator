-- Phase 1 foundation schema: companies, users, master_excel, quotations,
-- quotation_files, audit_logs. Purely additive - no existing route reads
-- from these tables yet. RLS is enabled on every table as defense-in-depth;
-- the FastAPI backend is the sole DB access path and sets
-- app.current_company_id / app.current_user_id / app.current_role per
-- request (see server/_db.py) so these policies are actually exercised
-- rather than bypassed by a superuser connection.

create extension if not exists "pgcrypto";

create table companies (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    display_name text not null,
    template_filename text not null,
    default_currency text not null default 'NRs',
    default_vat_rate numeric not null default 0,
    default_validity text not null default '30 days from the date of this quotation',
    terms_and_conditions jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table users (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    full_name text not null,
    username text not null,
    password_hash text not null,
    role text not null check (role in ('admin', 'staff')),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (company_id, username)
);

create table master_excel (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    storage_path text not null,
    original_filename text not null,
    uploaded_by uuid not null references users(id),
    uploaded_at timestamptz not null default now(),
    file_size bigint not null,
    -- only one active master Excel per company
    unique (company_id)
);

create table quotations (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    quote_number integer not null,
    customer_name text not null,
    created_by uuid not null references users(id),
    created_at timestamptz not null default now(),
    status text not null default 'final' check (status in ('final', 'pdf_pending')),
    docx_storage_path text not null,
    pdf_storage_path text,
    unique (company_id, quote_number)
);

create index quotations_company_created_by_idx on quotations(company_id, created_by);
create index quotations_company_created_at_idx on quotations(company_id, created_at desc);

create table quotation_files (
    id uuid primary key default gen_random_uuid(),
    quotation_id uuid not null references quotations(id) on delete cascade,
    kind text not null check (kind in ('docx', 'pdf')),
    storage_path text not null,
    size_bytes bigint not null,
    created_at timestamptz not null default now(),
    unique (quotation_id, kind)
);

create table audit_logs (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    user_id uuid references users(id),
    action text not null,
    entity_type text not null,
    entity_id text,
    ip_address text,
    user_agent text,
    metadata jsonb,
    created_at timestamptz not null default now()
);

create index audit_logs_company_created_at_idx on audit_logs(company_id, created_at desc);

-- Seed the one real company that exists today, matching
-- app/quotation_companies.py's hardcoded CompanyProfile exactly.
insert into companies (slug, display_name, template_filename, default_currency, default_vat_rate, default_validity, terms_and_conditions)
values (
    'garg_dental',
    'Garg Dental Pvt. Ltd',
    'equipment_proposal_garg_dental.docx',
    'NRs',
    0,
    '30 days from the date of this quotation',
    '[
        ["Prices", "Prices are in NRs on door delivery basis."],
        ["Taxes", "VAT is Inclusive as applicable."],
        ["Payment", "50% advance & balance remaining against delivery."],
        ["Delivery", "After 6-8 weeks after your confirmed order subject to meet the payment terms."],
        ["Shipment From", "Our warehouse in Kathmandu or from the location/company if it''s a direct shipment."],
        ["Purchase Order", "Must be in the name of Garg Dental Pvt. Ltd or in the name of the principal co."],
        ["Installation", "Installation of the equipment will be done by our engineers based in Kathmandu at no extra cost."],
        ["Warranty", "The equipment are warranted against manufacturing defects for a period of 24 months from the date of installation. All warranty replacement is subject to conditions."],
        ["Scope of Warranty", "Consumables, semi consumable, bulbs, probes, cables etc. are not covered under warranty. Reusable accessories are covered under limited warranty (Condition apply)."]
    ]'::jsonb
);

-- FORCE (not just ENABLE) matters here: the DATABASE_URL connection string
-- Supabase hands out connects as the table-owning role, and plain "enable
-- row level security" is bypassed automatically for owners. FORCE makes
-- these policies apply even to that connection, which is what makes them
-- real defense-in-depth instead of decorative - see server/_db.py for how
-- app.current_company_id/current_user_id/is_login_lookup get set per query.
alter table companies enable row level security;
alter table companies force row level security;
alter table users enable row level security;
alter table users force row level security;
alter table master_excel enable row level security;
alter table master_excel force row level security;
alter table quotations enable row level security;
alter table quotations force row level security;
alter table quotation_files enable row level security;
alter table quotation_files force row level security;
alter table audit_logs enable row level security;
alter table audit_logs force row level security;

-- current_setting(..., true) returns '' (not NULL) for a var this session
-- explicitly set to '' via set_config - which server/_db.py does whenever a
-- caller doesn't know that value yet (e.g. login, before any identity is
-- resolved). Casting '' straight to ::uuid raises an error rather than
-- just failing the policy, so every comparison below goes through
-- nullif(..., '') first to turn "not provided" into a clean NULL (a NULL
-- comparison is simply false/no-match, never an error).
create policy company_isolation on companies
    using (id = nullif(current_setting('app.current_company_id', true), '')::uuid);

-- users gets two OR'd policies (Postgres combines multiple permissive
-- policies on one table with OR): the standard company-scoped view for
-- routes that already know who's asking, plus self_read so a request
-- holding only a user_id (resolved from the session cookie, before we've
-- looked up that user's company_id) can still read its own row - otherwise
-- require_auth's "who is this cookie for" lookup would be locked out by
-- its own policy.
create policy company_isolation on users
    using (company_id = nullif(current_setting('app.current_company_id', true), '')::uuid);

create policy self_read on users
    using (id = nullif(current_setting('app.current_user_id', true), '')::uuid);

-- Login itself starts with neither a company_id nor a user_id - just a
-- submitted username - so it needs its own narrow escape hatch rather than
-- reusing self_read/company_isolation. app.is_login_lookup is set to
-- 'true' only inside server/_auth.py's login() function, nowhere else in
-- the codebase, which keeps this bypass auditable to one call site.
create policy login_lookup on users
    using (current_setting('app.is_login_lookup', true) = 'true');

create policy company_isolation on master_excel
    using (company_id = nullif(current_setting('app.current_company_id', true), '')::uuid);

create policy company_isolation on quotations
    using (company_id = nullif(current_setting('app.current_company_id', true), '')::uuid);

create policy company_isolation on quotation_files
    using (
        quotation_id in (
            select id from quotations
            where company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        )
    );

create policy company_isolation on audit_logs
    using (company_id = nullif(current_setting('app.current_company_id', true), '')::uuid);

-- Staff-only additional restriction on quotations: enforced in application
-- code (server/_quotation_history_routes.py) via an explicit created_by
-- filter, not RLS, since "admin sees all, staff sees own" depends on role,
-- which is cheaper and clearer to check in Python than a second RLS policy
-- layered on top of company_isolation. RLS here is the company-boundary
-- safety net, not the full authorization model.
