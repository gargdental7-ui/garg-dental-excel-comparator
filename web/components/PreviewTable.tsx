import type { ReactNode } from "react";

export interface PreviewColumn<T> {
  header: string;
  render: (row: T) => ReactNode;
}

export function PreviewTable<T>({
  rows,
  columns,
  totalCount,
  emptyMessage = "No rows.",
}: {
  rows: T[];
  columns: PreviewColumn<T>[];
  totalCount: number;
  emptyMessage?: string;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-sm">
        <thead className="bg-slate-50 dark:bg-slate-900">
          <tr>
            {columns.map((col) => (
              <th
                key={col.header}
                className="px-3 py-2 text-left font-medium text-slate-600 dark:text-slate-300 whitespace-nowrap"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {rows.map((row, i) => (
            <tr key={i} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50">
              {columns.map((col) => (
                <td key={col.header} className="px-3 py-2 whitespace-nowrap text-slate-800 dark:text-slate-200">
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {totalCount > rows.length && (
        <p className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
          Showing first {rows.length.toLocaleString()} of {totalCount.toLocaleString()}. The full list is in the
          exported Excel file.
        </p>
      )}
    </div>
  );
}
