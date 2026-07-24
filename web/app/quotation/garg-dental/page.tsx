import Link from "next/link";
import { FilePlus2, FolderOpen, FileSpreadsheet, LayoutTemplate, Settings, Clock } from "lucide-react";

const ACTIONS = [
  {
    href: "/quotation/garg-dental/new",
    icon: FilePlus2,
    title: "Create New Quote",
    description: "Start a fresh quotation - Excel-assisted or fully manual.",
    enabled: true,
  },
  {
    href: "#",
    icon: FolderOpen,
    title: "Open Draft",
    description: "Resume a quotation you started earlier.",
    enabled: false,
  },
  {
    href: "/quotation/garg-dental/new",
    icon: FileSpreadsheet,
    title: "Import Product Excel",
    description: "Jump straight into Excel-assisted mode with a product list.",
    enabled: true,
  },
  {
    href: "#",
    icon: LayoutTemplate,
    title: "Templates",
    description: "Manage the branded proposal template.",
    enabled: false,
  },
  {
    href: "#",
    icon: Settings,
    title: "Settings",
    description: "Terms & conditions, currency, and defaults.",
    enabled: false,
  },
];

// Placeholder data - no quotation is persisted server-side today (the app
// stays offline/stateless by design), so there is nothing real to list yet.
const RECENT_QUOTES: { customer: string; date: string; total: string }[] = [];

export default function GargDentalDashboardPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <Link href="/quotation" className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
        &larr; All Companies
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-50">Garg Dental Pvt. Ltd.</h1>
      <p className="mb-8 text-sm text-slate-600 dark:text-slate-400">Quotation Dashboard</p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ACTIONS.map(({ href, icon: Icon, title, description, enabled }) =>
          enabled ? (
            <Link
              key={title}
              href={href}
              className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
            >
              <Icon className="h-5 w-5 text-brand-cyan" />
              <h2 className="mt-3 text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h2>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>
            </Link>
          ) : (
            <div
              key={title}
              className="cursor-not-allowed rounded-lg border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-5 opacity-60"
            >
              <Icon className="h-5 w-5 text-slate-400" />
              <h2 className="mt-3 text-base font-semibold text-slate-700 dark:text-slate-300">{title}</h2>
              <p className="mt-1 text-sm text-slate-500">{description}</p>
              <span className="mt-2 inline-block text-xs font-semibold uppercase tracking-wide text-slate-400">
                Coming Soon
              </span>
            </div>
          )
        )}
      </div>

      <div className="mt-10">
        <div className="mb-3 flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Recent Quotes</h2>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
          {RECENT_QUOTES.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Nothing yet - quotations aren&apos;t stored on the server, so this fills in once local draft history is
              added.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {RECENT_QUOTES.map((q) => (
                <li key={q.customer} className="flex justify-between py-2 text-sm">
                  <span>{q.customer}</span>
                  <span className="text-slate-500">{q.date}</span>
                  <span className="font-semibold">{q.total}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
