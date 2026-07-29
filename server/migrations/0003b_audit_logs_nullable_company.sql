-- Follow-up to 0003_multi_tenant.sql, found while wiring log_action() call
-- sites through to the new company-scoping model: audit_logs.company_id
-- was NOT NULL, but a super_admin's own actions (e.g. their own login)
-- aren't scoped to any single company. The company_isolation RLS policy
-- already handles NULL correctly (it never matches any specific
-- company's session, but the is_super_admin bypass still sees it), so
-- this is a safe, additive relaxation.
alter table audit_logs alter column company_id drop not null;
