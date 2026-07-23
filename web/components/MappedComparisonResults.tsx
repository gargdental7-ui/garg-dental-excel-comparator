"use client";

import type { ComparatorAnalyzeMappedResponse, MappedProductRow } from "@/lib/types";
import { StatsPanel } from "@/components/StatsPanel";
import { PreviewTable, type PreviewColumn } from "@/components/PreviewTable";

function fmt(value: unknown) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function buildColumns(result: ComparatorAnalyzeMappedResponse): PreviewColumn<MappedProductRow>[] {
  const columns: PreviewColumn<MappedProductRow>[] = [{ header: "Code", render: (r) => r.code }];
  result.stats.mappings.forEach((mapping, i) => {
    columns.push({
      header: `${mapping.current_column} (Current)`,
      render: (r) => fmt(r.fields[i]?.current_value),
    });
    columns.push({
      header: `${mapping.latest_column} (Latest)`,
      render: (r) => fmt(r.fields[i]?.latest_value),
    });
  });
  return columns;
}

export function MappedComparisonResults({ result }: { result: ComparatorAnalyzeMappedResponse }) {
  const columns = buildColumns(result);
  const changedColumns: PreviewColumn<MappedProductRow>[] = [
    ...columns,
    { header: "Changed Fields", render: (r) => r.changed_field_labels.join(", ") },
  ];

  return (
    <div className="space-y-4">
      <StatsPanel
        items={[
          { label: "Products Compared", value: result.stats.total_compared.toLocaleString() },
          { label: "Rows Changed", value: result.stats.total_changed.toLocaleString() },
          { label: "Rows Unchanged", value: result.stats.total_unchanged.toLocaleString() },
          { label: "Added Products", value: result.stats.total_added.toLocaleString() },
          { label: "Removed Products", value: result.stats.total_removed.toLocaleString() },
        ]}
      />

      {result.stats.duplicate_warnings.length > 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
          <p className="mb-1 font-semibold">Duplicate Codes Found</p>
          <ul className="list-disc pl-5">
            {result.stats.duplicate_warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Changed Products</p>
        <PreviewTable<MappedProductRow>
          rows={result.changed_preview}
          totalCount={result.changed_total_count}
          emptyMessage="No changed products were found."
          columns={changedColumns}
        />
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Added Products</p>
        <PreviewTable<MappedProductRow>
          rows={result.added_preview}
          totalCount={result.added_total_count}
          emptyMessage="No new products were found."
          columns={columns}
        />
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Removed Products</p>
        <PreviewTable<MappedProductRow>
          rows={result.removed_preview}
          totalCount={result.removed_total_count}
          emptyMessage="No removed products were found."
          columns={columns}
        />
      </div>
    </div>
  );
}
