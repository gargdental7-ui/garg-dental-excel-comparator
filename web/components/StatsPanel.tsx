export interface StatItem {
  label: string;
  value: string;
}

export function StatsPanel({ items }: { items: StatItem[] }) {
  return (
    <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
      {items.map((item) => (
        <div key={item.label}>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {item.label}
          </dt>
          <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-50">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
