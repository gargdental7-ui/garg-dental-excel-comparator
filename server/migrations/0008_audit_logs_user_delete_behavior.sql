-- Bug found via live testing: deleting a user via DELETE /api/users/{id}
-- raised a raw ForeignKeyViolation (surfaced to the client as a generic
-- 500 "Unexpected error occurred") whenever that user had any audit log
-- history, since audit_logs.user_id had no ON DELETE behavior specified
-- (defaults to NO ACTION - blocks the delete). The right behavior is
-- ON DELETE SET NULL, not CASCADE: a user's past actions should stay in
-- the audit trail even after the account is deleted (audit_logs.user_id
-- was already nullable for exactly this reason), not vanish, and
-- shouldn't block deletion either.
alter table audit_logs drop constraint audit_logs_user_id_fkey;
alter table audit_logs add constraint audit_logs_user_id_fkey
    foreign key (user_id) references users(id) on delete set null;
