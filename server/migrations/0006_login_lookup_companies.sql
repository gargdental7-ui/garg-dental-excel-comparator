-- Bug found via live multi-tenant testing: server/_auth.py's login query
-- joins users to companies (to check company_active alongside the user's
-- own active flag), but the login_lookup RLS escape hatch only existed on
-- the users table. During login, app.is_login_lookup='true' is set but
-- neither app.is_super_admin nor app.current_company_id are - so the
-- companies side of the join was invisible under RLS, making
-- company_active NULL for every row and failing every staff login
-- (NULL is falsy, so "company_id is not null and not company_active"
-- always tripped). Same escape-hatch pattern as users.login_lookup,
-- audited to the same one call site in server/_auth.py.
create policy login_lookup on companies
    using (current_setting('app.is_login_lookup', true) = 'true');
