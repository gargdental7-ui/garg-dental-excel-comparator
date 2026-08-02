-- Phase I: AI-driven company onboarding. A super_admin uploads whatever
-- documents a prospective company already has (past quotations, product
-- catalogues, brochures) and Claude extracts a company profile and full
-- product catalog automatically. Every extracted value carries a
-- confidence score so the review wizard can flag anything below 85% for
-- manual confirmation before publish.
--
-- companies gains the profile columns onboarding extracts - all nullable
-- so existing companies (Garg Dental) keep working with them unset.
alter table companies add column company_code text;
alter table companies add column industry text;
alter table companies add column address text;
alter table companies add column email text;
alter table companies add column phone text;
alter table companies add column website text;
alter table companies add column vat_number text;

create table onboarding_sessions (
    id uuid primary key default gen_random_uuid(),
    created_by uuid not null references users(id),
    -- Null until publish creates the real company row (step 2 of the
    -- publish flow) - this is also why these four new tables can't use the
    -- usual company_isolation RLS shape (there's no company_id to scope by
    -- for most of a session's life).
    company_id uuid references companies(id) on delete set null,
    status text not null default 'draft' check (status in ('draft', 'reviewing', 'published')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    published_at timestamptz
);

create table onboarding_documents (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references onboarding_sessions(id) on delete cascade,
    filename text not null,
    storage_path text not null,
    document_type text not null default 'other' check (document_type in ('quotation', 'catalog', 'brochure', 'image', 'other')),
    uploaded_at timestamptz not null default now(),
    extraction_status text not null default 'pending' check (extraction_status in ('pending', 'processing', 'done', 'failed')),
    extraction_error text
);

create table onboarding_company_fields (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references onboarding_sessions(id) on delete cascade,
    field_name text not null,
    extracted_value text,
    confidence real not null default 0,
    source_document_id uuid references onboarding_documents(id) on delete set null,
    -- Null until the wizard user edits/confirms it; the publish flow
    -- prefers reviewed_value over extracted_value when set.
    reviewed_value text,
    unique (session_id, field_name)
);

create table onboarding_products (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references onboarding_sessions(id) on delete cascade,
    product_name text not null,
    code text not null default '',
    description text not null default '',
    brand text not null default '',
    model text not null default '',
    origin text not null default '',
    category text not null default '',
    warranty text not null default '',
    price numeric not null default 0,
    mrp numeric not null default 0,
    confidence real not null default 0,
    source_document_id uuid references onboarding_documents(id) on delete set null,
    duplicate_of_product_id uuid references onboarding_products(id) on delete set null,
    image_storage_path text,
    -- Lets a reviewer exclude a bogus/duplicate extraction from publish
    -- without losing the row (and its provenance) entirely.
    included boolean not null default true
);

alter table onboarding_sessions enable row level security;
alter table onboarding_sessions force row level security;
alter table onboarding_documents enable row level security;
alter table onboarding_documents force row level security;
alter table onboarding_company_fields enable row level security;
alter table onboarding_company_fields force row level security;
alter table onboarding_products enable row level security;
alter table onboarding_products force row level security;

-- Every onboarding route is super_admin-only (server/_onboarding_routes.py
-- gates every endpoint with require_super_admin), so there's no company to
-- scope these by - same plain-flag escape-hatch shape as login_lookup on
-- users (0001_initial_schema.sql), just gated on is_super_admin instead.
create policy super_admin_only on onboarding_sessions
    using (current_setting('app.is_super_admin', true) = 'true');
create policy super_admin_only on onboarding_documents
    using (current_setting('app.is_super_admin', true) = 'true');
create policy super_admin_only on onboarding_company_fields
    using (current_setting('app.is_super_admin', true) = 'true');
create policy super_admin_only on onboarding_products
    using (current_setting('app.is_super_admin', true) = 'true');
