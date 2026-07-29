"use client";

import { useEffect, useState } from "react";
import { Building2 } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { Table, type TableColumn } from "@/components/ui/Table";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { Company } from "@/lib/types";

function CreateCompanyModal({ onClose, onCreated }: { onClose: () => void; onCreated: (company: Company) => void }) {
  const [slug, setSlug] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const company = await api.companies.create({ slug, display_name: displayName });
      onCreated(company);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not create the company.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "mb-3 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500";

  return (
    <Modal title="Add Company" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Company Name</label>
        <input required value={displayName} onChange={(e) => setDisplayName(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Slug <span className="font-normal text-slate-400">(lowercase, no spaces - e.g. air_experts)</span>
        </label>
        <input
          required
          pattern="[a-z0-9_]+"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          className={inputClass}
        />

        {error && <ErrorBanner message={error} />}

        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Company"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function CompaniesPage() {
  const me = useCurrentUser();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    if (me?.role !== "super_admin") return;
    let cancelled = false;
    api.companies
      .list()
      .then((res) => {
        if (!cancelled) setCompanies(res.companies);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load companies.");
      });
    return () => {
      cancelled = true;
    };
  }, [me]);

  async function toggleActive(company: Company) {
    try {
      const updated = await api.companies.update(company.id, { active: !company.active });
      setCompanies((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not update the company.");
    }
  }

  async function removeCompany(company: Company) {
    if (!confirm(`Delete ${company.displayName}? This only works if it has no quotations on record.`)) return;
    try {
      await api.companies.remove(company.id);
      setCompanies((prev) => prev.filter((c) => c.id !== company.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not delete the company.");
    }
  }

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={Building2} title="Companies" description="Manage every company on the platform." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  const columns: TableColumn<Company>[] = [
    { header: "Name", render: (c) => c.displayName },
    { header: "Slug", render: (c) => c.slug },
    {
      header: "Status",
      render: (c) => (
        <button
          onClick={() => toggleActive(c)}
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            c.active
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400"
              : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
          }`}
        >
          {c.active ? "Active" : "Disabled"}
        </button>
      ),
    },
    {
      header: "Actions",
      render: (c) => (
        <button
          onClick={() => removeCompany(c)}
          className="text-xs font-medium text-red-500 hover:text-red-700 dark:hover:text-red-400"
        >
          Delete
        </button>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageHeader icon={Building2} title="Companies" description="Manage every company on the platform." />

      <div className="mb-4 flex justify-end">
        <Button onClick={() => setShowCreate(true)}>Add Company</Button>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <Table columns={columns} rows={companies} rowKey={(c) => c.id} emptyMessage="No companies yet." />

      {companies.length > 0 && (
        <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
          {companies.filter((c) => !c.active).length > 0 && (
            <>
              <Badge>Disabled</Badge> companies&apos; staff can no longer log in, but their data is kept.
            </>
          )}
        </p>
      )}

      {showCreate && (
        <CreateCompanyModal onClose={() => setShowCreate(false)} onCreated={(c) => setCompanies((prev) => [...prev, c])} />
      )}
    </div>
  );
}
