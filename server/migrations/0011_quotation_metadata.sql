-- Phase E: expanded quotation metadata - records which signature was used
-- and which template/master-Excel *version* was active at generation time,
-- so a quotation stays auditable even after the company later replaces its
-- template or master Excel. version starts at 1 and increments on every
-- upsert (upload_master_excel/upload_template already upsert on
-- conflict(company_id) since only one active version is kept per company).
alter table master_excel add column version integer not null default 1;
alter table quotation_templates add column version integer not null default 1;

alter table quotations add column signature_id uuid references signatures(id) on delete set null;
alter table quotations add column template_version integer;
alter table quotations add column master_excel_version integer;
