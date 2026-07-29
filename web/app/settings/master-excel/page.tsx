"use client";

import { useEffect, useState } from "react";
import { FileSpreadsheet } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { FileDropInput } from "@/components/FileDropInput";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { CurrentUser, MasterExcelMetadata } from "@/lib/types";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function MasterExcelSettingsPage() {
  const [me, setMe] = useState<CurrentUser | null | undefined>(undefined);
  const [meta, setMeta] = useState<MasterExcelMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.auth
      .status()
      .then((status) => setMe(status.user ?? null))
      .catch(() => setMe(null));
  }, []);

  useEffect(() => {
    if (me?.role !== "admin") return;
    api.masterExcel
      .getMetadata()
      .then(setMeta)
      .catch((err) => setError(err instanceof ApiError ? err.detail.message : "Could not load master Excel status."));
  }, [me]);

  async function handleUpload(file: File) {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.masterExcel.upload(file);
      setMeta(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not upload the file.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete the Company Master Excel? Staff will no longer be able to use it for new quotations.")) return;
    setBusy(true);
    setError(null);
    try {
      await api.masterExcel.remove();
      setMeta({ exists: false });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not delete the file.");
    } finally {
      setBusy(false);
    }
  }

  if (me === undefined) return null;

  if (me === null || me.role !== "admin") {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <PageHeader icon={FileSpreadsheet} title="Master Excel Library" description="Manage the company-wide product Excel." />
        <ErrorBanner message="You need admin access to view this page." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <PageHeader
        icon={FileSpreadsheet}
        title="Master Excel Library"
        description="Upload one permanent product Excel that staff can reuse for every quotation without uploading it again."
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {meta?.exists && (
        <div className="mb-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="h-8 w-8 shrink-0 text-brand-navy dark:text-brand-cyan" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{meta.filename}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatFileSize(meta.fileSize)} · Uploaded by {meta.uploadedBy} on{" "}
                {new Date(meta.uploadedAt).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <a href={api.masterExcel.downloadUrl}>
              <Button variant="secondary">Download</Button>
            </a>
            <Button variant="danger" onClick={handleDelete} disabled={busy}>
              Delete
            </Button>
          </div>
        </div>
      )}

      <FileDropInput
        label={meta?.exists ? "Replace Master Excel" : "Upload Master Excel"}
        fileName={null}
        onChange={handleUpload}
      />
      {busy && <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Working...</p>}
    </div>
  );
}
