"use client";

import type { ExcelPreviewRow } from "@/lib/types";

export function ExcelPreviewTable({
  rows,
  headerRow,
  onSelectRow,
}: {
  rows: ExcelPreviewRow[];
  headerRow: number | null;
  onSelectRow: (row: number) => void;
}) {
  const columnCount = rows.reduce((max, r) => Math.max(max, r.values.length), 0);

  if (rows.length === 0) {
    return null;
  }

  return (
    <div className="overflow-auto rounded-md border border-slate-200 dark:border-slate-800" style={{ maxHeight: 320 }}>
      <table className="min-w-full border-collapse text-xs">
        <tbody>
          {rows.map((r) => {
            const isHeader = r.row === headerRow;
            return (
              <tr
                key={r.row}
                onClick={() => onSelectRow(r.row)}
                className={
                  "cursor-pointer transition-colors " +
                  (isHeader
                    ? "bg-brand-cyan/10 dark:bg-brand-cyan/20"
                    : "odd:bg-white even:bg-slate-50 hover:bg-slate-100 dark:odd:bg-slate-900 dark:even:bg-slate-900/60 dark:hover:bg-slate-800")
                }
                title={isHeader ? `Row ${r.row} - current header row` : `Click to use row ${r.row} as the header row`}
              >
                <td
                  className={
                    "sticky left-0 whitespace-nowrap border-r border-slate-200 px-2 py-1 text-right font-mono tabular-nums dark:border-slate-800 " +
                    (isHeader
                      ? "bg-brand-cyan/20 font-semibold text-brand-navy dark:bg-brand-cyan/30 dark:text-brand-cyan"
                      : "bg-inherit text-slate-400 dark:text-slate-500")
                  }
                >
                  {r.row}
                  {isHeader && <span className="ml-1">&larr;</span>}
                </td>
                {Array.from({ length: columnCount }).map((_, i) => (
                  <td
                    key={i}
                    className={
                      "whitespace-nowrap px-2 py-1 " +
                      (isHeader ? "font-semibold text-slate-900 dark:text-slate-50" : "text-slate-600 dark:text-slate-400")
                    }
                  >
                    {r.values[i] || ""}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
