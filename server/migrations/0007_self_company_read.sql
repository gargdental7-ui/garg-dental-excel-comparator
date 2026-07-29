-- Same underlying gap as 0006, one layer deeper: server/_auth.py's
-- require_auth -> _load_user_by_id(user_id) also joins users to companies
-- (to re-check company_active on every request, not just at login), but
-- at that point we only know user_id (from the session cookie) - not yet
-- their company_id, so app.current_company_id can't be set in advance and
-- the companies side of the join is invisible under RLS again.
--
-- This policy resolves "which company does the current session's user
-- belong to" via a subquery against users (itself protected by users'
-- own self_read policy, so this doesn't leak anything new), rather than
-- requiring the caller to already know the answer - mirrors self_read on
-- users, one hop further.
create policy self_company_read on companies
    using (
        id = (
            select company_id from users
            where id = nullif(current_setting('app.current_user_id', true), '')::uuid
        )
    );
