-- Phase A of the multi-company redesign: collapses the per-company
-- admin/staff role pair into a two-tier model (super_admin spans every
-- company, staff stays scoped to exactly one) instead of adding a third
-- tier - confirmed directly with the user rather than assumed. The
-- existing 'admin' role is retired; there is no more per-company admin.

-- users.company_id must become nullable: a super_admin belongs to the
-- parent organization, not any single company.
alter table users alter column company_id drop not null;

-- Drop the old role check constraint first so the data migration below
-- isn't blocked by either the old vocabulary (rejects 'super_admin') or a
-- premature new one (would reject the still-in-place 'admin' row before
-- it's been updated).
alter table users drop constraint users_role_check;

-- Promote the existing Garg Dental admin account to the one global Super
-- Admin - confirmed with the user rather than creating a separate new
-- account. Must run before the new constraints below, which require
-- super_admin rows to have no company_id.
update users set role = 'super_admin', company_id = null where username = 'admin' and role = 'admin';

-- Now that data matches, add the new two-role vocabulary plus a second
-- constraint tying the nullability of company_id to the role - a
-- super_admin must have no company_id, a staff member must have one. This
-- is what makes "does this user have a company" a reliable signal
-- elsewhere in the code instead of something that could silently drift
-- out of sync.
alter table users add constraint users_role_check check (role in ('super_admin', 'staff'));
alter table users add constraint users_role_company_id_check
    check ((role = 'super_admin' and company_id is null) or (role = 'staff' and company_id is not null));

-- Companies gain an active flag so Super Admin can disable one without
-- deleting its data (disabling blocks that company's staff from logging
-- in and hides it from company selectors, per Phase B).
alter table companies add column active boolean not null default true;

-- Every existing company_isolation policy gets OR'd with a super-admin
-- bypass. app.is_super_admin is derived automatically in server/_db.py
-- from the role already passed to get_connection() - no route needs to
-- pass anything new. This is the same escape-hatch pattern already used
-- for login_lookup on the users table, not a new RLS concept.
drop policy company_isolation on companies;
create policy company_isolation on companies
    using (
        id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );

drop policy company_isolation on users;
create policy company_isolation on users
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );

drop policy company_isolation on master_excel;
create policy company_isolation on master_excel
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );

drop policy company_isolation on quotations;
create policy company_isolation on quotations
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );

drop policy company_isolation on quotation_files;
create policy company_isolation on quotation_files
    using (
        quotation_id in (
            select id from quotations
            where company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        )
        or current_setting('app.is_super_admin', true) = 'true'
    );

drop policy company_isolation on audit_logs;
create policy company_isolation on audit_logs
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );

drop policy company_isolation on quote_number_counters;
create policy company_isolation on quote_number_counters
    using (
        company_id = nullif(current_setting('app.current_company_id', true), '')::uuid
        or current_setting('app.is_super_admin', true) = 'true'
    );
