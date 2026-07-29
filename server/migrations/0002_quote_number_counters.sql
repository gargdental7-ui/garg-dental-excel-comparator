-- Phase 4: stable, company-scoped quote numbers. default_output_filename()
-- previously used date+customer-name only, which collides once quotations
-- are actually persisted (two quotes for the same customer on the same day
-- would overwrite each other's storage path). One row per company, atomic
-- increment-and-fetch via the upsert in server/_quotation_routes.py.
create table quote_number_counters (
    company_id uuid primary key references companies(id) on delete cascade,
    next_number integer not null default 1
);

alter table quote_number_counters enable row level security;
alter table quote_number_counters force row level security;

create policy company_isolation on quote_number_counters
    using (company_id = nullif(current_setting('app.current_company_id', true), '')::uuid);
