"use client";

import { CheckCircle2 } from "lucide-react";

export function HeaderRowSelector({
  detectedRow,
  headerRow,
  maxRow,
  onChange,
}: {
  detectedRow: number | null;
  headerRow: number | null;
  maxRow: number;
  onChange: (row: number) => void;
}) {
  const usingDetected = detectedRow !== null && headerRow === detectedRow;

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/50">
      <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Header Row</p>

      {detectedRow !== null ? (
        <p className="mb-2 flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-brand-cyan" />
          Automatically detected header row: <span className="font-semibold">Row {detectedRow}</span>
        </p>
      ) : (
        <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
          We couldn&apos;t automatically determine the header row.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-slate-700 dark:text-slate-300" htmlFor="header-row-input">
          {detectedRow !== null ? "Or select manually:" : "Select the row that holds the column titles:"}
        </label>
        <input
          id="header-row-input"
          type="number"
          min={1}
          max={maxRow}
          value={headerRow ?? ""}
          onChange={(e) => {
            const value = Number(e.target.value);
            if (value >= 1 && value <= maxRow) onChange(value);
          }}
          className="w-20 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        />
        {detectedRow !== null && !usingDetected && (
          <button
            type="button"
            onClick={() => onChange(detectedRow)}
            className="text-sm font-medium text-brand-navy hover:underline dark:text-brand-cyan"
          >
            Use detected row
          </button>
        )}
        {usingDetected && (
          <span className="inline-flex items-center gap-1 text-sm font-medium text-brand-cyan">
            <CheckCircle2 className="h-4 w-4" />
            Using detected row
          </span>
        )}
      </div>

      <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
        Click any row in the preview above, or type a row number, to change it - the preview and column mapping
        update instantly.
      </p>
    </div>
  );
}
