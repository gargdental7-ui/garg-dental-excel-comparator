"use client";

import type { ColumnMappingPair } from "@/lib/types";

const SELECT_CLASS =
  "w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100";

export function ColumnMappingBuilder({
  currentHeaders,
  omsHeaders,
  mappings,
  onChange,
}: {
  currentHeaders: string[];
  omsHeaders: string[];
  mappings: ColumnMappingPair[];
  onChange: (next: ColumnMappingPair[]) => void;
}) {
  function updatePair(index: number, key: keyof ColumnMappingPair, value: string) {
    const next = mappings.slice();
    next[index] = { ...next[index], [key]: value };
    onChange(next);
  }

  function removePair(index: number) {
    onChange(mappings.filter((_, i) => i !== index));
  }

  function addPair() {
    const usedCurrent = new Set(mappings.map((m) => m.current_column));
    const usedLatest = new Set(mappings.map((m) => m.latest_column));
    const nextCurrent = currentHeaders.find((h) => !usedCurrent.has(h)) ?? currentHeaders[0] ?? "";
    const nextLatest = omsHeaders.find((h) => !usedLatest.has(h)) ?? omsHeaders[0] ?? "";
    onChange([...mappings, { current_column: nextCurrent, latest_column: nextLatest }]);
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">Column Mapping</p>
        <button type="button" onClick={addPair} className="text-xs font-medium text-slate-600 dark:text-slate-300 hover:underline">
          + Add Column
        </button>
      </div>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Pair up each column you want to compare - the two files don&apos;t need matching column names (e.g. Current
        &quot;Balance&quot; with Latest &quot;Available Stock&quot;). Comparing one identically-named column keeps
        today&apos;s export format; two or more (or a renamed pair) produces the fuller Column Comparison Report.
      </p>

      {mappings.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No columns mapped yet.</p>
      ) : (
        <div className="space-y-2">
          <div className="hidden gap-3 sm:grid sm:grid-cols-[1fr_1fr_auto] sm:text-xs sm:font-medium sm:text-slate-500 dark:sm:text-slate-400">
            <span>Current Workbook</span>
            <span>Latest Workbook</span>
            <span />
          </div>
          {mappings.map((pair, i) => (
            <div key={i} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto] sm:items-center">
              <select
                value={pair.current_column}
                onChange={(e) => updatePair(i, "current_column", e.target.value)}
                className={SELECT_CLASS}
              >
                {currentHeaders.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              <select
                value={pair.latest_column}
                onChange={(e) => updatePair(i, "latest_column", e.target.value)}
                className={SELECT_CLASS}
              >
                {omsHeaders.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removePair(i)}
                className="justify-self-start text-sm text-slate-400 hover:text-red-600 dark:hover:text-red-400 sm:justify-self-center"
                aria-label={`Remove ${pair.current_column} / ${pair.latest_column} mapping`}
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
