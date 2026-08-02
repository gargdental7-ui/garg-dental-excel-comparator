"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, ImageIcon, PenSquare, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { OnboardingSessionDetail, PublishOnboardingResponse } from "@/lib/types";

const CONFIDENCE_THRESHOLD = 0.85;

const FIELD_LABELS: Record<string, string> = {
  company_name: "Company Name",
  company_code: "Company Code",
  industry: "Industry",
  address: "Address",
  email: "Email",
  phone: "Phone",
  website: "Website",
  vat_number: "VAT / Tax Number",
};

const IMAGE_FIELD_LABELS: Record<string, string> = {
  logo_storage_path: "Logo",
  signature_storage_path: "Signature",
};

function ConfidenceBadge({ confidence }: { confidence: number }) {
  if (confidence >= CONFIDENCE_THRESHOLD) return <Badge tone="success">{Math.round(confidence * 100)}%</Badge>;
  return <Badge tone="warning">{Math.round(confidence * 100)}% - review</Badge>;
}

function EditableCell({ value, onSave }: { value: string; onSave: (next: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => {
          setDraft(value);
          setEditing(true);
        }}
        className="inline-flex items-center gap-1.5 text-left hover:text-brand-navy dark:hover:text-brand-cyan"
      >
        <span className="truncate">{value || <span className="text-slate-400">-</span>}</span>
        <PenSquare className="h-3 w-3 shrink-0 opacity-40" />
      </button>
    );
  }

  return (
    <input
      autoFocus
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => {
        setEditing(false);
        if (draft !== value) onSave(draft);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
        if (e.key === "Escape") {
          setDraft(value);
          setEditing(false);
        }
      }}
      className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
    />
  );
}

function PublishModal({
  sessionId,
  suggestedName,
  onClose,
  onPublished,
}: {
  sessionId: string;
  suggestedName: string;
  onClose: () => void;
  onPublished: (result: PublishOnboardingResponse) => void;
}) {
  const [slug, setSlug] = useState(suggestedName.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, ""));
  const [adminUsername, setAdminUsername] = useState("");
  const [adminFullName, setAdminFullName] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.onboarding.publish(sessionId, {
        slug,
        admin_username: adminUsername,
        admin_full_name: adminFullName,
        admin_password: adminPassword,
      });
      onPublished(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not publish this company.");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "mb-3 w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500";

  return (
    <Modal title="Publish Company" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          Slug <span className="font-normal text-slate-400">(lowercase, no spaces)</span>
        </label>
        <input required pattern="[a-z0-9_]+" value={slug} onChange={(e) => setSlug(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">First Admin - Username</label>
        <input required value={adminUsername} onChange={(e) => setAdminUsername(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">First Admin - Full Name</label>
        <input required value={adminFullName} onChange={(e) => setAdminFullName(e.target.value)} className={inputClass} />

        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
          First Admin - Password <span className="font-normal text-slate-400">(min 8 characters)</span>
        </label>
        <input
          required
          minLength={8}
          type="text"
          value={adminPassword}
          onChange={(e) => setAdminPassword(e.target.value)}
          className={inputClass}
        />

        {error && <ErrorBanner message={error} />}

        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Publishing..." : "Publish Company"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default function OnboardingReviewPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const me = useCurrentUser();
  const [detail, setDetail] = useState<OnboardingSessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPublish, setShowPublish] = useState(false);
  const [published, setPublished] = useState<PublishOnboardingResponse | null>(null);

  function reload() {
    api.onboarding
      .getSession(params.sessionId)
      .then(setDetail)
      .catch((err) => setError(err instanceof ApiError ? err.detail.message : "Could not load this onboarding session."));
  }

  useEffect(() => {
    if (me?.role !== "super_admin") return;
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me, params.sessionId]);

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <PageHeader icon={Sparkles} title="Review Onboarding" description="AI-assisted company onboarding." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  if (published) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <PageHeader icon={Sparkles} title="Company Published" description="The new company is live and ready to use." />
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 dark:border-emerald-900 dark:bg-emerald-950">
          <div className="mb-3 flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="h-5 w-5" />
            <p className="font-semibold">{published.productCount} products imported.</p>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300">
            First admin login: <span className="font-mono font-semibold">{published.adminUsername}</span> (the password you set)
          </p>
        </div>
        <div className="mt-4 flex justify-end">
          <Button onClick={() => router.push(`/companies/${published.companyId}/dashboard`)}>Go to Company Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="mx-auto max-w-5xl p-6">
        <PageHeader icon={Sparkles} title="Review Onboarding" description="AI-assisted company onboarding." />
        {error && <ErrorBanner message={error} />}
      </div>
    );
  }

  const { companyFields, products, duplicateGroups } = detail;
  const profileFields = companyFields.filter((f) => f.fieldName in FIELD_LABELS);
  const imageFields = companyFields.filter((f) => f.fieldName in IMAGE_FIELD_LABELS);
  const duplicateProductIds = new Set(duplicateGroups.flat());
  const lowConfidenceCount =
    profileFields.filter((f) => f.confidence < CONFIDENCE_THRESHOLD).length +
    products.filter((p) => p.included && p.confidence < CONFIDENCE_THRESHOLD).length;

  function fieldValue(fieldName: string): string {
    const field = companyFields.find((f) => f.fieldName === fieldName);
    return field?.reviewedValue ?? field?.extractedValue ?? "";
  }

  async function saveField(fieldName: string, value: string) {
    const next = await api.onboarding.updateField(params.sessionId, fieldName, value);
    setDetail(next);
  }

  async function saveProduct(productId: string, patch: Record<string, unknown>) {
    const next = await api.onboarding.updateProduct(params.sessionId, productId, patch);
    setDetail(next);
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <PageHeader
        icon={Sparkles}
        title="Review Extraction"
        description="Confirm the AI-extracted company profile and product catalog before publishing. Anything below 85% confidence is flagged for your review."
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {lowConfidenceCount > 0 && (
        <div className="mb-4">
          <Badge tone="warning">{lowConfidenceCount} field(s) need your review</Badge>
        </div>
      )}

      <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Company Profile</h2>
        <dl className="grid gap-3 sm:grid-cols-2">
          {Object.entries(FIELD_LABELS).map(([fieldName, label]) => {
            const field = profileFields.find((f) => f.fieldName === fieldName);
            return (
              <div key={fieldName} className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2 dark:border-slate-800">
                <div className="min-w-0 flex-1">
                  <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
                  <dd className="text-sm text-slate-800 dark:text-slate-100">
                    <EditableCell value={fieldValue(fieldName)} onSave={(v) => saveField(fieldName, v)} />
                  </dd>
                </div>
                {field && <ConfidenceBadge confidence={field.confidence} />}
              </div>
            );
          })}
        </dl>
        {imageFields.length > 0 && (
          <div className="mt-4 flex gap-2">
            {imageFields.map((f) => (
              <span
                key={f.fieldName}
                className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              >
                <ImageIcon className="h-3.5 w-3.5" />
                {IMAGE_FIELD_LABELS[f.fieldName]} detected
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="mb-6 rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
          Products ({products.filter((p) => p.included).length} included)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="py-2 pr-3">Product</th>
                <th className="py-2 pr-3">Code</th>
                <th className="py-2 pr-3">Price</th>
                <th className="py-2 pr-3">Confidence</th>
                <th className="py-2 pr-3"></th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr
                  key={p.id}
                  className={
                    "border-b border-slate-100 dark:border-slate-800 " +
                    (!p.included ? "opacity-40" : duplicateProductIds.has(p.id) ? "bg-amber-50 dark:bg-amber-950/30" : "")
                  }
                >
                  <td className="py-2 pr-3">
                    <EditableCell value={p.productName} onSave={(v) => saveProduct(p.id, { product_name: v })} />
                    {duplicateProductIds.has(p.id) && (
                      <span className="ml-1 text-xs text-amber-600 dark:text-amber-400">possible duplicate</span>
                    )}
                  </td>
                  <td className="py-2 pr-3">
                    <EditableCell value={p.code} onSave={(v) => saveProduct(p.id, { code: v })} />
                  </td>
                  <td className="py-2 pr-3">
                    <EditableCell
                      value={String(p.price)}
                      onSave={(v) => saveProduct(p.id, { price: Number(v) || 0 })}
                    />
                  </td>
                  <td className="py-2 pr-3">
                    <ConfidenceBadge confidence={p.confidence} />
                  </td>
                  <td className="py-2 pr-3">
                    <button
                      type="button"
                      onClick={() => saveProduct(p.id, { included: !p.included })}
                      className="text-xs font-medium text-slate-500 hover:text-red-600 dark:hover:text-red-400"
                    >
                      {p.included ? "Exclude" : "Include"}
                    </button>
                  </td>
                </tr>
              ))}
              {products.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-400">
                    No products extracted yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="flex justify-end">
        <Button onClick={() => setShowPublish(true)} disabled={!fieldValue("company_name") || products.filter((p) => p.included).length === 0}>
          Publish Company
        </Button>
      </div>

      {showPublish && (
        <PublishModal
          sessionId={params.sessionId}
          suggestedName={fieldValue("company_name")}
          onClose={() => setShowPublish(false)}
          onPublished={(result) => {
            setShowPublish(false);
            setPublished(result);
          }}
        />
      )}
    </div>
  );
}
