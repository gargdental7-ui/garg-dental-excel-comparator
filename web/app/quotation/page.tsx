import Link from "next/link";
import { Lock } from "lucide-react";
import { COMPANIES } from "@/lib/companies";

export default function QuotationCompanySelectPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50">Smart Quotation Generator</h1>
      <p className="mb-8 text-sm text-slate-600 dark:text-slate-400">
        Select a company to build a quotation for. Each company has its own branding, template, and terms - the
        quotation engine underneath is shared.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {COMPANIES.map((company) =>
          company.active ? (
            <Link
              key={company.id}
              href={`/quotation/${company.id.replace("_", "-")}`}
              className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 transition hover:border-slate-400 dark:hover:border-slate-600 hover:shadow-md"
            >
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{company.displayName}</h2>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{company.tagline}</p>
              <span className="mt-3 inline-block text-xs font-semibold uppercase tracking-wide text-brand-cyan">
                Fully Functional
              </span>
            </Link>
          ) : (
            <div
              key={company.id}
              className="cursor-not-allowed rounded-lg border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-5 opacity-60"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300">{company.displayName}</h2>
                <Lock className="h-4 w-4 text-slate-400" />
              </div>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-500">{company.tagline}</p>
              <span className="mt-3 inline-block text-xs font-semibold uppercase tracking-wide text-slate-400">
                Coming Soon
              </span>
            </div>
          )
        )}
      </div>
    </div>
  );
}
