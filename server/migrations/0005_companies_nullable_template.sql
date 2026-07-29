-- A brand-new company created by the Super Admin (Phase B) has no
-- quotation template yet - that gets uploaded separately afterward
-- (Phase C moves templates to per-company Storage uploads entirely,
-- replacing this column's original "static file in the repo" meaning).
-- Nullable so company creation doesn't require a template up front.
alter table companies alter column template_filename drop not null;
