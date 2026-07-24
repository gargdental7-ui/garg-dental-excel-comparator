"use client";

export function ColumnChecklist({
  columns,
  selected,
  onChange,
}: {
  columns: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  if (columns.length === 0) return null;

  function toggle(col: string) {
    const next = new Set(selected);
    if (next.has(col)) next.delete(col);
    else next.add(col);
    onChange(next);
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Columns To Compare</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onChange(new Set(columns))}
            className="text-xs font-medium text-slate-600 dark:text-slate-300 hover:underline"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={() => onChange(new Set())}
            className="text-xs font-medium text-slate-600 dark:text-slate-300 hover:underline"
          >
            Select None
          </button>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {columns.map((col) => (
          <label key={col} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="checkbox" checked={selected.has(col)} onChange={() => toggle(col)} />
            {col}
          </label>
        ))}
      </div>
    </div>
  );
}
