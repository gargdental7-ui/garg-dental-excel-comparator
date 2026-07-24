"use client";

export function ColumnMappingField({
  label,
  required,
  headers,
  value,
  onChange,
}: {
  label: string;
  required?: boolean;
  headers: string[];
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  const NONE = "-- None --";
  return (
    <div className="flex items-center gap-3 py-1">
      <label className="w-56 shrink-0 text-sm text-slate-700 dark:text-slate-300">
        {label}
        {required ? " *" : ""}
      </label>
      <select
        value={value ?? (required ? "" : NONE)}
        onChange={(e) => onChange(e.target.value === NONE ? null : e.target.value)}
        className="w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100"
      >
        {!required && <option value={NONE}>{NONE}</option>}
        {required && value === null && <option value="">-- Select --</option>}
        {headers.map((h) => (
          <option key={h} value={h}>
            {h}
          </option>
        ))}
      </select>
    </div>
  );
}
