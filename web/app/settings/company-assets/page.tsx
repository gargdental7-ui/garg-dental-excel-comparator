"use client";

import { useEffect, useState } from "react";
import { FileText, Image as ImageIcon, Layers, PenTool } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { FileDropInput } from "@/components/FileDropInput";
import { CompanySelector } from "@/components/CompanySelector";
import { Badge } from "@/components/ui/Badge";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { CompanyLogoMetadata, QuotationTemplateMetadata, SignatureSummary } from "@/lib/types";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function CompanyAssetsSettingsPage() {
  const me = useCurrentUser();
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [templateMeta, setTemplateMeta] = useState<QuotationTemplateMetadata | null>(null);
  const [logoMeta, setLogoMeta] = useState<CompanyLogoMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [templateBusy, setTemplateBusy] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);

  const [signatures, setSignatures] = useState<SignatureSummary[]>([]);
  const [signatureBusy, setSignatureBusy] = useState(false);
  const [newSignatureName, setNewSignatureName] = useState("");
  const [newSignatureDesignation, setNewSignatureDesignation] = useState("");
  const [newSignatureFile, setNewSignatureFile] = useState<File | null>(null);

  useEffect(() => {
    if (me?.role !== "super_admin" || !companyId) return;
    let cancelled = false;
    Promise.all([
      api.companyAssets.getTemplateMetadata(companyId),
      api.companyAssets.getLogoMetadata(companyId),
      api.signatures.list(companyId),
    ])
      .then(([template, logo, sigRes]) => {
        if (cancelled) return;
        setTemplateMeta(template);
        setLogoMeta(logo);
        setSignatures(sigRes.signatures);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail.message : "Could not load company assets.");
      });
    return () => {
      cancelled = true;
    };
  }, [me, companyId]);

  async function handleTemplateUpload(file: File) {
    if (!companyId) return;
    setTemplateBusy(true);
    setError(null);
    try {
      const updated = await api.companyAssets.uploadTemplate(file, companyId);
      setTemplateMeta(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not upload the template.");
    } finally {
      setTemplateBusy(false);
    }
  }

  async function handleTemplateDelete() {
    if (!companyId) return;
    if (!confirm("Delete this company's quotation template? Staff will not be able to generate quotations until a new one is uploaded."))
      return;
    setTemplateBusy(true);
    setError(null);
    try {
      await api.companyAssets.removeTemplate(companyId);
      setTemplateMeta({ exists: false });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not delete the template.");
    } finally {
      setTemplateBusy(false);
    }
  }

  async function handleLogoUpload(file: File) {
    if (!companyId) return;
    setLogoBusy(true);
    setError(null);
    try {
      const updated = await api.companyAssets.uploadLogo(file, companyId);
      setLogoMeta(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not upload the logo.");
    } finally {
      setLogoBusy(false);
    }
  }

  async function handleLogoDelete() {
    if (!companyId) return;
    if (!confirm("Delete this company's logo? It will no longer appear on new quotations.")) return;
    setLogoBusy(true);
    setError(null);
    try {
      await api.companyAssets.removeLogo(companyId);
      setLogoMeta({ exists: false });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not delete the logo.");
    } finally {
      setLogoBusy(false);
    }
  }

  async function handleSignatureCreate() {
    if (!companyId || !newSignatureFile || !newSignatureName.trim()) return;
    setSignatureBusy(true);
    setError(null);
    try {
      const created = await api.signatures.create(newSignatureFile, companyId, newSignatureName.trim(), newSignatureDesignation.trim());
      setSignatures((prev) => [...prev, created]);
      setNewSignatureName("");
      setNewSignatureDesignation("");
      setNewSignatureFile(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not add the signature.");
    } finally {
      setSignatureBusy(false);
    }
  }

  async function handleSignatureToggleActive(signature: SignatureSummary) {
    if (!companyId) return;
    setSignatureBusy(true);
    setError(null);
    try {
      const updated = await api.signatures.update(signature.id, companyId, { active: !signature.active });
      setSignatures((prev) => prev.map((s) => (s.id === signature.id ? updated : s)));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not update the signature.");
    } finally {
      setSignatureBusy(false);
    }
  }

  async function handleSignatureDelete(signature: SignatureSummary) {
    if (!companyId) return;
    if (!confirm(`Delete the signature "${signature.name}"? This cannot be undone.`)) return;
    setSignatureBusy(true);
    setError(null);
    try {
      await api.signatures.remove(signature.id, companyId);
      setSignatures((prev) => prev.filter((s) => s.id !== signature.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not delete the signature.");
    } finally {
      setSignatureBusy(false);
    }
  }

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <PageHeader icon={Layers} title="Company Assets" description="Manage a company's quotation template and logo." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <PageHeader
        icon={Layers}
        title="Company Assets"
        description="Upload a company's quotation template and logo, used every time that company's staff generate a quotation."
      />

      <div className="mb-4">
        <CompanySelector value={companyId} onChange={setCompanyId} />
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {companyId && (
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <FileText className="h-4 w-4 text-brand-navy dark:text-brand-cyan" />
              Quotation Template
            </h2>
            {templateMeta?.exists && (
              <div className="mb-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
                <div className="flex items-center gap-3">
                  <FileText className="h-8 w-8 shrink-0 text-brand-navy dark:text-brand-cyan" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{templateMeta.filename}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {formatFileSize(templateMeta.fileSize)} · Uploaded by {templateMeta.uploadedBy} on{" "}
                      {new Date(templateMeta.uploadedAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <a href={api.companyAssets.downloadTemplateUrl(companyId)}>
                    <Button variant="secondary">Download</Button>
                  </a>
                  <Button variant="danger" onClick={handleTemplateDelete} disabled={templateBusy}>
                    Delete
                  </Button>
                </div>
              </div>
            )}
            <FileDropInput
              label={templateMeta?.exists ? "Replace Quotation Template" : "Upload Quotation Template"}
              fileName={null}
              onChange={handleTemplateUpload}
              accept=".docx"
              hint="Word documents"
              icon={FileText}
            />
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Any real Word (.docx) document can be uploaded. See{" "}
              <code className="rounded bg-slate-100 px-1 py-0.5 dark:bg-slate-800">docs/quotation-template-tags.md</code> for the
              placeholder tags a template can use, and how to add a watermark.
            </p>
            {templateBusy && <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Working...</p>}
          </section>

          <section>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <ImageIcon className="h-4 w-4 text-brand-navy dark:text-brand-cyan" />
              Company Logo
            </h2>
            {logoMeta?.exists && (
              <div className="mb-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
                <div className="flex items-center gap-3">
                  <ImageIcon className="h-8 w-8 shrink-0 text-brand-navy dark:text-brand-cyan" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Logo uploaded</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Uploaded on {new Date(logoMeta.uploadedAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button variant="danger" onClick={handleLogoDelete} disabled={logoBusy}>
                    Delete
                  </Button>
                </div>
              </div>
            )}
            <FileDropInput
              label={logoMeta?.exists ? "Replace Logo" : "Upload Logo"}
              fileName={null}
              onChange={handleLogoUpload}
              accept=".png,.jpg,.jpeg,.webp"
              hint="Images"
              icon={ImageIcon}
            />
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Only appears on quotations if the company&rsquo;s template includes the <code className="rounded bg-slate-100 px-1 py-0.5 dark:bg-slate-800">{"{{ company_logo }}"}</code> tag.
            </p>
            {logoBusy && <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Working...</p>}
          </section>

          <section>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
              <PenTool className="h-4 w-4 text-brand-navy dark:text-brand-cyan" />
              Signature Library
            </h2>

            {signatures.length > 0 && (
              <div className="mb-3 space-y-2">
                {signatures.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{s.name}</p>
                        <Badge tone={s.active ? "success" : "neutral"}>{s.active ? "Active" : "Inactive"}</Badge>
                      </div>
                      {s.designation && <p className="text-xs text-slate-500 dark:text-slate-400">{s.designation}</p>}
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Button variant="secondary" onClick={() => handleSignatureToggleActive(s)} disabled={signatureBusy}>
                        {s.active ? "Disable" : "Enable"}
                      </Button>
                      <Button variant="danger" onClick={() => handleSignatureDelete(s)} disabled={signatureBusy}>
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
              <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Add Signature</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  type="text"
                  placeholder="Name (e.g. Dr. R. Garg)"
                  value={newSignatureName}
                  onChange={(e) => setNewSignatureName(e.target.value)}
                  className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
                <input
                  type="text"
                  placeholder="Designation (e.g. Director)"
                  value={newSignatureDesignation}
                  onChange={(e) => setNewSignatureDesignation(e.target.value)}
                  className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
              <div className="mt-2">
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp"
                  onChange={(e) => setNewSignatureFile(e.target.files?.[0] ?? null)}
                  className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-brand-navy/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-brand-navy hover:file:bg-brand-navy/20 dark:text-slate-400 dark:file:bg-brand-cyan/10 dark:file:text-brand-cyan"
                />
              </div>
              <div className="mt-3">
                <Button
                  onClick={handleSignatureCreate}
                  disabled={signatureBusy || !newSignatureFile || !newSignatureName.trim()}
                >
                  {signatureBusy ? "Working..." : "Add Signature"}
                </Button>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
