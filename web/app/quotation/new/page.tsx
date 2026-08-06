"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, downloadBlob } from "@/lib/apiClient";
import {
  ApiError,
  type QuotationCustomer,
  type QuotationImportedProduct,
  type QuotationItem,
  type QuotationProposal,
  type SignatureSummary,
} from "@/lib/types";
import { blankQuotationItem, defaultQuotationProposal, emptyQuotationCustomer, quotationItemFromImportedProduct } from "@/lib/quotationDefaults";
import { computeTotals } from "@/lib/quotationTotals";
import { findDuplicateProducts } from "@/lib/quotationValidation";
import { CustomerInfoForm } from "@/components/quotation/CustomerInfoForm";
import { ProposalInfoForm } from "@/components/quotation/ProposalInfoForm";
import { ModeSelectCards, type QuotationMode } from "@/components/quotation/ModeSelectCards";
import { ProductImportPanel } from "@/components/quotation/ProductImportPanel";
import { ProductBrowser } from "@/components/quotation/ProductBrowser";
import { ProductForm } from "@/components/quotation/ProductForm";
import { ProductCard } from "@/components/quotation/ProductCard";
import { QuoteSummary } from "@/components/quotation/QuoteSummary";
import { QuotationHelp } from "@/components/quotation/QuotationHelp";
import { QuotationPreview } from "@/components/quotation/QuotationPreview";
import { ErrorBanner } from "@/components/ErrorBanner";
import { Button } from "@/components/Button";

// Nothing here is ever sent anywhere until "Generate DOCX" - this is purely
// a local, in-browser draft so a refresh (or an accidental tab close)
// doesn't lose an in-progress quotation. Versioned key so a future change
// to the draft shape can't crash on an old stored draft.
const DRAFT_STORAGE_KEY = "gd_quotation_draft_v1";

interface QuotationDraft {
  customer: QuotationCustomer;
  proposal: QuotationProposal;
  mode: QuotationMode | null;
  items: QuotationItem[];
  excelProducts: QuotationImportedProduct[] | null;
  excelFileName: string;
}

function stripClientId(item: QuotationItem): Omit<QuotationItem, "id"> {
  const rest: Partial<QuotationItem> = { ...item };
  delete rest.id;
  return rest as Omit<QuotationItem, "id">;
}

type ItemsAction =
  | { type: "add"; item: QuotationItem }
  | { type: "update"; id: string; item: QuotationItem }
  | { type: "duplicate"; id: string }
  | { type: "delete"; id: string }
  | { type: "load"; items: QuotationItem[] };

function itemsReducer(state: QuotationItem[], action: ItemsAction): QuotationItem[] {
  switch (action.type) {
    case "add":
      return [...state, action.item];
    case "update":
      return state.map((it) => (it.id === action.id ? action.item : it));
    case "duplicate": {
      const found = state.find((it) => it.id === action.id);
      if (!found) return state;
      return [...state, { ...found, id: `${found.id}-copy-${Date.now()}` }];
    }
    case "delete":
      return state.filter((it) => it.id !== action.id);
    case "load":
      return action.items;
    default:
      return state;
  }
}

function NewQuotePage() {
  const searchParams = useSearchParams();
  const companyId = searchParams.get("company_id");

  const [customer, setCustomer] = useState<QuotationCustomer>(emptyQuotationCustomer());
  const [proposal, setProposal] = useState<QuotationProposal>(defaultQuotationProposal());
  const [mode, setMode] = useState<QuotationMode | null>(null);

  const [excelProducts, setExcelProducts] = useState<QuotationImportedProduct[] | null>(null);
  const [excelFileName, setExcelFileName] = useState("");

  const [items, dispatchItems] = useReducer(itemsReducer, []);
  const [formSeed, setFormSeed] = useState<QuotationItem | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formImagePathHint, setFormImagePathHint] = useState("");

  const [signatures, setSignatures] = useState<SignatureSummary[]>([]);
  const [signatureId, setSignatureId] = useState<string>("");

  const [busy, setBusy] = useState(false);
  const [busyPdf, setBusyPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totals = useMemo(() => computeTotals(items, 0), [items]);
  const duplicateProducts = useMemo(() => findDuplicateProducts(items), [items]);

  useEffect(() => {
    if (!companyId) return;
    let cancelled = false;
    api.signatures
      .list(companyId)
      .then((res) => {
        if (!cancelled) setSignatures(res.signatures);
      })
      .catch(() => {
        // Non-fatal - the signature picker is optional, quotations can
        // still be generated without one.
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  // Restore a draft left over from before a refresh/close. Done in an
  // effect (not a useState lazy initializer) so server and first-client
  // render both start from the same empty defaults - no hydration mismatch.
  const [hydrated, setHydrated] = useState(false);
  /* eslint-disable react-hooks/set-state-in-effect --
     localStorage can only be read client-side, and this must run exactly
     once after mount to seed React state from it - there is no prop/state
     this could be derived from instead, so the usual "don't setState in an
     effect" guidance doesn't apply here. */
  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (raw) {
        const draft = JSON.parse(raw) as Partial<QuotationDraft>;
        if (draft.customer) setCustomer(draft.customer);
        if (draft.proposal) setProposal(draft.proposal);
        if (draft.mode) setMode(draft.mode);
        if (Array.isArray(draft.items)) dispatchItems({ type: "load", items: draft.items });
        if (Array.isArray(draft.excelProducts)) setExcelProducts(draft.excelProducts);
        if (draft.excelFileName) setExcelFileName(draft.excelFileName);
      }
    } catch {
      // Corrupt or old-shape draft - ignore it and start fresh rather than
      // block the page from loading.
    } finally {
      setHydrated(true);
    }
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Autosave, debounced so typing in a text field doesn't stringify/write
  // on every keystroke. Gated on `hydrated` so this can't fire with the
  // still-empty initial state and clobber a draft before it's been read.
  useEffect(() => {
    if (!hydrated) return;
    const timeout = setTimeout(() => {
      const draft: QuotationDraft = { customer, proposal, mode, items, excelProducts, excelFileName };
      try {
        localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
      } catch {
        // Most likely quota exceeded from embedded product images (base64
        // data URLs) - retry once without them rather than losing the rest
        // of the draft (customer/proposal/line items) entirely.
        try {
          const withoutImages = { ...draft, items: items.map((it) => ({ ...it, image: null })) };
          localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(withoutImages));
        } catch {
          // Persistence is a convenience, not a requirement - give up quietly.
        }
      }
    }, 400);
    return () => clearTimeout(timeout);
  }, [hydrated, customer, proposal, mode, items, excelProducts, excelFileName]);

  // The form renders wherever it was triggered from (e.g. below a long
  // Browse Products list), often outside the current viewport - without
  // this, clicking "Select" looks like nothing happened.
  const formRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (formSeed) {
      formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [formSeed]);

  function openManualForm() {
    setFormSeed(blankQuotationItem());
    setEditingId(null);
    setFormImagePathHint("");
  }

  function openFormFromProduct(product: QuotationImportedProduct) {
    setFormSeed(quotationItemFromImportedProduct(product));
    setEditingId(null);
    setFormImagePathHint(product.image_path);
  }

  function openEditForm(item: QuotationItem) {
    setFormSeed(item);
    setEditingId(item.id);
    setFormImagePathHint("");
  }

  function closeForm() {
    setFormSeed(null);
    setEditingId(null);
    setFormImagePathHint("");
  }

  function handleFormSave(item: QuotationItem) {
    if (editingId) {
      dispatchItems({ type: "update", id: editingId, item });
    } else {
      dispatchItems({ type: "add", item });
    }
    closeForm();
  }

  function validateBeforeGenerate(): boolean {
    if (!companyId) {
      setError("No company selected. Go back and pick a company first.");
      return false;
    }
    if (!customer.customer_name.trim()) {
      setError("Please enter a Customer Name before generating the quotation.");
      return false;
    }
    if (items.length === 0) {
      setError("Please add at least one product before generating the quotation.");
      return false;
    }
    if (duplicateProducts.length > 0) {
      setError(`The following product(s) were added more than once: ${duplicateProducts.join(", ")}.`);
      return false;
    }
    return true;
  }

  async function handleGenerate() {
    setError(null);
    if (!validateBeforeGenerate()) return;
    setBusy(true);
    try {
      const { blob, filename } = await api.quotation.generate({
        company_id: companyId!,
        customer,
        proposal,
        items: items.map((item) => stripClientId(item)),
        signature_id: signatureId || undefined,
      });
      downloadBlob(blob, filename);
      // The quotation is done and downloaded - a refresh from here on
      // should start clean rather than keep restoring a finished draft.
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setBusy(false);
    }
  }

  // Generates a PDF from the server: fill data -> insert signature -> insert
  // images -> save DOCX -> convert that DOCX to PDF. This replaced a
  // window.print() of the on-screen preview, which had no signature and
  // could show broken-image boxes since it was an unrelated, hand-coded
  // HTML approximation of the real template rather than a conversion of it.
  async function handleGeneratePdf() {
    setError(null);
    if (!validateBeforeGenerate()) return;
    setBusyPdf(true);
    try {
      const { blob, filename } = await api.quotation.generatePdf({
        company_id: companyId!,
        customer,
        proposal,
        items: items.map((item) => stripClientId(item)),
        signature_id: signatureId || undefined,
      });
      downloadBlob(blob, filename);
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail.message : "An unexpected error occurred.");
    } finally {
      setBusyPdf(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div>
        <Link href="/quotation" prefetch={false} className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          &larr; Quotation Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-50">Smart Quotation Generator</h1>
        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
          Build a professional proposal in minutes - upload a product Excel, or add products manually.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <QuotationHelp />
          <ErrorBanner message={error} />

          <CustomerInfoForm value={customer} onChange={setCustomer} />
          <ProposalInfoForm value={proposal} onChange={setProposal} />

          <ModeSelectCards mode={mode} onChange={setMode} />

          {mode === "excel" && !excelProducts && (
            <ProductImportPanel
              companyId={companyId ?? undefined}
              onImported={(products, fileName) => {
                setExcelProducts(products);
                setExcelFileName(fileName);
              }}
            />
          )}

          {mode === "excel" && excelProducts && (
            <>
              <ProductBrowser products={excelProducts} fileName={excelFileName} onSelect={openFormFromProduct} />
              <Button variant="secondary" onClick={openManualForm}>
                New Manual Product
              </Button>
            </>
          )}

          {mode === "manual" && (
            <Button onClick={openManualForm}>New Manual Product</Button>
          )}

          {formSeed && (
            <div ref={formRef}>
              <ProductForm
                initialValue={formSeed}
                isEditing={!!editingId}
                imagePathHint={formImagePathHint}
                onSave={handleFormSave}
                onCancel={closeForm}
              />
            </div>
          )}

          {items.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                Selected Products ({items.length})
              </p>
              {duplicateProducts.length > 0 && (
                <div className="rounded-md border border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
                  Added more than once: {duplicateProducts.join(", ")}. Edit the quantity on one card instead, or
                  remove the duplicate before generating.
                </div>
              )}
              {items.map((item) => (
                <ProductCard
                  key={item.id}
                  item={item}
                  onEdit={() => openEditForm(item)}
                  onDuplicate={() => dispatchItems({ type: "duplicate", id: item.id })}
                  onDelete={() => dispatchItems({ type: "delete", id: item.id })}
                />
              ))}
            </div>
          )}

          {items.length > 0 && (
            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
              <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Review &amp; Generate</p>

              {signatures.length > 0 && (
                <div className="mb-3">
                  <label htmlFor="signature" className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Signature (optional)
                  </label>
                  <select
                    id="signature"
                    value={signatureId}
                    onChange={(e) => setSignatureId(e.target.value)}
                    className="w-full max-w-xs rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-500"
                  >
                    <option value="">No signature</option>
                    {signatures.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                        {s.designation ? ` - ${s.designation}` : ""}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <Button onClick={handleGenerate} disabled={busy || busyPdf || duplicateProducts.length > 0}>
                  {busy ? "Generating..." : "Generate DOCX"}
                </Button>
                <Button variant="secondary" onClick={handleGeneratePdf} disabled={busy || busyPdf || duplicateProducts.length > 0}>
                  {busyPdf ? "Generating..." : "Generate PDF"}
                </Button>
              </div>
            </div>
          )}
        </div>

        <div>
          <QuoteSummary totals={totals} currency={proposal.currency || "NRs"} itemCount={items.length} />
        </div>
      </div>

      {/* Rough on-screen draft preview only - not what "Generate DOCX" /
          "Generate PDF" produce. Those come from the server rendering the
          company's actual uploaded template (with the real signature and
          images), which this simplified HTML approximation can't reflect. */}
      {items.length > 0 && (
        <div className="mt-6 max-h-[600px] overflow-y-auto">
          <QuotationPreview customer={customer} proposal={proposal} items={items} totals={totals} />
        </div>
      )}
    </div>
  );
}

export default function NewQuotePageWrapper() {
  return (
    <Suspense fallback={null}>
      <NewQuotePage />
    </Suspense>
  );
}
