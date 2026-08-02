"use client";

import { useEffect, useRef, useState, type DragEvent } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2, Sparkles, Upload, XCircle } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";
import { useCurrentUser } from "@/lib/useCurrentUser";
import { api } from "@/lib/apiClient";
import { ApiError } from "@/lib/types";
import type { OnboardingDocument } from "@/lib/types";

const ACCEPT = "application/pdf,image/png,image/jpeg";

function StatusIcon({ status }: { status: OnboardingDocument["extractionStatus"] }) {
  if (status === "done") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red-500" />;
  return <Loader2 className="h-4 w-4 animate-spin text-slate-400" />;
}

export default function NewOnboardingPage() {
  const me = useCurrentUser();
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<OnboardingDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (me?.role !== "super_admin" || startedRef.current) return;
    startedRef.current = true;
    api.onboarding
      .createSession()
      .then((session) => setSessionId(session.id))
      .catch((err) => setError(err instanceof ApiError ? err.detail.message : "Could not start onboarding."));
  }, [me]);

  async function uploadFiles(files: FileList | File[]) {
    if (!sessionId) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const detail = await api.onboarding.uploadDocument(sessionId, file);
        setDocuments(detail.documents);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "Could not upload one of the documents.");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) uploadFiles(e.dataTransfer.files);
  }

  if (me === undefined) return null;

  if (me === null || me.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <PageHeader icon={Sparkles} title="Onboard New Company" description="AI-assisted company onboarding." />
        <ErrorBanner message="You need Super Admin access to view this page." />
      </div>
    );
  }

  const anyDone = documents.some((d) => d.extractionStatus === "done");
  const anyProcessing = documents.some((d) => d.extractionStatus === "pending" || d.extractionStatus === "processing");

  return (
    <div className="mx-auto max-w-3xl p-6">
      <PageHeader
        icon={Sparkles}
        title="Onboard New Company"
        description="Upload past quotations, product catalogues, or brochures - Claude will extract the company profile and full product catalog automatically."
      />

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-12 text-center transition-colors " +
          (dragging
            ? "border-brand-cyan bg-brand-cyan/5 dark:bg-brand-cyan/10"
            : "border-slate-300 hover:border-brand-cyan/50 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800/50")
        }
      >
        <Upload className={"h-8 w-8 " + (dragging ? "text-brand-cyan" : "text-slate-400")} />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          <span className="font-semibold text-brand-navy dark:text-brand-cyan">Click to upload</span> or drag and
          drop - one or several documents at once
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500">PDF quotations/catalogues, or logo/signature images (PNG, JPG)</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          disabled={!sessionId || uploading}
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) uploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </label>

      {documents.length > 0 && (
        <ul className="mt-4 space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center gap-3 rounded-md border border-slate-200 bg-white px-4 py-2.5 text-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <StatusIcon status={doc.extractionStatus} />
              <span className="min-w-0 flex-1 truncate text-slate-800 dark:text-slate-200">{doc.filename}</span>
              {doc.extractionStatus === "failed" && doc.extractionError && (
                <span className="shrink-0 text-xs text-red-500">{doc.extractionError}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 flex justify-end">
        <Button
          disabled={!sessionId || !anyDone || anyProcessing || uploading}
          onClick={() => sessionId && router.push(`/onboarding/${sessionId}/review`)}
        >
          Continue to Review
        </Button>
      </div>
    </div>
  );
}
