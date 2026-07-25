"use client";

import Link from "next/link";
import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { api, downloadBlob } from "@/lib/apiClient";
import { ApiError, type QuotationCustomer, type QuotationImportedProduct, type QuotationItem, type QuotationProposal } from "@/lib/types";
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

const COMPANY_ID = "garg_dental";

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

export default function GargDentalNewQuotePage() {
  const [customer, setCustomer] = useState<QuotationCustomer>(emptyQuotationCustomer());
  const [proposal, setProposal] = useState<QuotationProposal>(defaultQuotationProposal());
  const [mode, setMode] = useState<QuotationMode | null>(null);

  const [excelProducts, setExcelProducts] = useState<QuotationImportedProduct[] | null>(null);
  const [excelFileName, setExcelFileName] = useState("");

  const [items, dispatchItems] = useReducer(itemsReducer, []);
  const [formSeed, setFormSeed] = useState<QuotationItem | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formImagePathHint, setFormImagePathHint] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totals = useMemo(() => computeTotals(items, 0), [items]);
  const duplicateProducts = useMemo(() => findDuplicateProducts(items), [items]);

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

  async function handleGenerate() {
    setError(null);
    if (!customer.customer_name.trim()) {
      setError("Please enter a Customer Name before generating the quotation.");
      return;
    }
    if (items.length === 0) {
      setError("Please add at least one product before generating the quotation.");
      return;
    }
    if (duplicateProducts.length > 0) {
      setError(`The following product(s) were added more than once: ${duplicateProducts.join(", ")}.`);
      return;
    }
    setBusy(true);
    try {
      const { blob, filename } = await api.quotation.generate({
        company_id: COMPANY_ID,
        customer,
        proposal,
        items: items.map((item) => stripClientId(item)),
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

  function handlePrint() {
    window.print();
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 print:max-w-none print:px-0 print:py-0">
      <div className="print:hidden">
        <Link
          href="/quotation/garg-dental"
          className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
        >
          &larr; Garg Dental Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-50">Smart Quotation Generator</h1>
        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
          Build a professional Garg Dental proposal in minutes - upload a product Excel, or add products manually.
        </p>
      </div>

      <div className="grid gap-6 print:block lg:grid-cols-[1fr_320px]">
        <div className="space-y-4 print:hidden">
          <QuotationHelp />
          <ErrorBanner message={error} />

          <CustomerInfoForm value={customer} onChange={setCustomer} />
          <ProposalInfoForm value={proposal} onChange={setProposal} />

          <ModeSelectCards mode={mode} onChange={setMode} />

          {mode === "excel" && !excelProducts && (
            <ProductImportPanel
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
              <div className="flex flex-wrap gap-3">
                <Button onClick={handleGenerate} disabled={busy || duplicateProducts.length > 0}>
                  {busy ? "Generating..." : "Generate DOCX"}
                </Button>
                <Button variant="secondary" onClick={handlePrint}>
                  Print / Save as PDF
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="print:hidden">
          <QuoteSummary totals={totals} currency={proposal.currency || "NRs"} itemCount={items.length} />
        </div>
      </div>

      {/* The one and only preview instance - visible on screen for review,
          and also the print target for "Print / Save as PDF" (see the
          #quotation-print-area isolation rule in globals.css). Living
          outside the print:hidden column above avoids ever having two
          copies (and two duplicate ids) in the DOM at once. */}
      {items.length > 0 && (
        <div className="mt-6 max-h-[600px] overflow-y-auto print:mt-0 print:max-h-none print:overflow-visible">
          <QuotationPreview customer={customer} proposal={proposal} items={items} totals={totals} />
        </div>
      )}
    </div>
  );
}
