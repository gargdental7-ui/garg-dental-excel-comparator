"use client";

import { useState } from "react";
import type { QuotationItem } from "@/lib/types";
import { Button } from "@/components/Button";

const INPUT_CLASS =
  "w-full rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100";
const LABEL_CLASS = "mb-1 block text-sm text-slate-700 dark:text-slate-300";

function TextField({
  label,
  value,
  onChange,
  required,
  textarea,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  textarea?: boolean;
}) {
  return (
    <div>
      <label className={LABEL_CLASS}>
        {label}
        {required ? " *" : ""}
      </label>
      {textarea ? (
        <textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)} className={INPUT_CLASS} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className={INPUT_CLASS} />
      )}
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  required,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  required?: boolean;
}) {
  // Local string state, not `value` directly: a controlled number input
  // whose displayed value is the numeric state itself snaps back to "0"
  // the instant the field is cleared (empty string -> onChange(0) ->
  // re-render with value=0), making it impossible to type a fresh number
  // or a decimal ("12." would round-trip back to "12", eating the dot).
  // `lastPushed` (plain state, not a ref - refs can't be read/written
  // during render) lets an external change (Edit/Duplicate/reset) still
  // sync the display, without every keystroke's own onChange stomping
  // what the user is mid-typing.
  const [text, setText] = useState(String(value));
  const [lastPushed, setLastPushed] = useState(value);
  if (value !== lastPushed) {
    setLastPushed(value);
    if (text !== String(value)) setText(String(value));
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value;
    setText(raw);
    if (raw === "" || raw === "-") {
      setLastPushed(0);
      onChange(0);
      return;
    }
    const parsed = Number(raw);
    if (!Number.isNaN(parsed)) {
      setLastPushed(parsed);
      onChange(parsed);
    }
  }

  return (
    <div>
      <label className={LABEL_CLASS}>
        {label}
        {required ? " *" : ""}
      </label>
      <input type="number" value={text} onChange={handleChange} className={INPUT_CLASS} />
    </div>
  );
}

function StringListEditor({ label, values, onChange }: { label: string; values: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState("");

  function add() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    onChange([...values, trimmed]);
    setDraft("");
  }

  return (
    <div>
      <label className={LABEL_CLASS}>{label}</label>
      {values.length > 0 && (
        <ul className="mb-2 space-y-1">
          {values.map((v, i) => (
            <li
              key={i}
              className="flex items-center justify-between gap-2 rounded-md border border-slate-200 dark:border-slate-700 px-2 py-1 text-sm text-slate-700 dark:text-slate-200"
            >
              <span className="min-w-0 flex-1">{v}</span>
              <button
                type="button"
                onClick={() => onChange(values.filter((_, idx) => idx !== i))}
                className="shrink-0 text-slate-400 hover:text-red-600 dark:hover:text-red-400"
                aria-label={`Remove ${v}`}
              >
                &times;
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          className={INPUT_CLASS}
          placeholder={`Add a line, press Enter`}
        />
        <button
          type="button"
          onClick={add}
          className="shrink-0 rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function readBlobAsDataUrl(blob: Blob): Promise<string> {
  return readFileAsDataUrl(blob as File);
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value.trim());
}

export function ProductForm({
  initialValue,
  isEditing,
  imagePathHint,
  onSave,
  onCancel,
}: {
  initialValue: QuotationItem;
  isEditing: boolean;
  imagePathHint?: string;
  onSave: (item: QuotationItem) => void;
  onCancel: () => void;
}) {
  const [item, setItem] = useState<QuotationItem>(initialValue);
  const [imageError, setImageError] = useState<string | null>(null);
  const [loadingImageUrl, setLoadingImageUrl] = useState(false);

  function set<K extends keyof QuotationItem>(key: K, value: QuotationItem[K]) {
    setItem((prev) => ({ ...prev, [key]: value }));
  }

  async function handleImageChange(file: File | null) {
    setImageError(null);
    if (!file) {
      set("image", null);
      return;
    }
    if (!file.type.startsWith("image/")) {
      setImageError("Please choose an image file.");
      return;
    }
    try {
      const dataUrl = await readFileAsDataUrl(file);
      set("image", dataUrl);
    } catch {
      setImageError("Could not read that image file.");
    }
  }

  async function handleLoadImageFromUrl() {
    if (!imagePathHint) return;
    setImageError(null);
    setLoadingImageUrl(true);
    try {
      const res = await fetch(imagePathHint);
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      if (!blob.type.startsWith("image/")) throw new Error("not an image");
      const dataUrl = await readBlobAsDataUrl(blob);
      set("image", dataUrl);
    } catch {
      setImageError("Could not load an image from that URL. You can still upload one manually.");
    } finally {
      setLoadingImageUrl(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!item.product_name.trim() || item.price <= 0) return;
    onSave(item);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4"
    >
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
        {isEditing ? "Edit Product" : "Add Product"}
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        <TextField label="Product Name" required value={item.product_name} onChange={(v) => set("product_name", v)} />
        <TextField label="Code" value={item.code} onChange={(v) => set("code", v)} />
        <TextField label="Brand" value={item.brand} onChange={(v) => set("brand", v)} />
        <TextField label="Model" value={item.model} onChange={(v) => set("model", v)} />
        <TextField label="Origin" value={item.origin} onChange={(v) => set("origin", v)} />
        <TextField label="Category" value={item.category} onChange={(v) => set("category", v)} />
        <NumberField label="Price" required value={item.price} onChange={(v) => set("price", v)} />
        <NumberField label="MRP" value={item.mrp} onChange={(v) => set("mrp", v)} />
        <NumberField label="Quantity" required value={item.quantity} onChange={(v) => set("quantity", v)} />
        <NumberField label="Discount %" value={item.discount_percent} onChange={(v) => set("discount_percent", v)} />
        <NumberField label="Discount Amount" value={item.discount_amount} onChange={(v) => set("discount_amount", v)} />
        <TextField label="Warranty" value={item.warranty} onChange={(v) => set("warranty", v)} />
        <div className="sm:col-span-2">
          <TextField label="Description" textarea value={item.description} onChange={(v) => set("description", v)} />
        </div>

        <div className="sm:col-span-2">
          <label className={LABEL_CLASS}>Product Image</label>
          <div className="flex flex-wrap items-center gap-3">
            {item.image && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={item.image}
                alt="Product preview"
                className="h-16 w-16 rounded-md border border-slate-300 dark:border-slate-700 object-cover"
              />
            )}
            <label className="inline-flex cursor-pointer items-center rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800">
              {item.image ? "Replace Image" : "Upload Image"}
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                className="hidden"
                onChange={(e) => handleImageChange(e.target.files?.[0] ?? null)}
              />
            </label>
            {item.image && (
              <button
                type="button"
                onClick={() => set("image", null)}
                className="text-sm text-slate-500 hover:text-red-600 dark:hover:text-red-400"
              >
                Remove
              </button>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">PNG, JPG, JPEG, or WEBP.</p>

          {!item.image && imagePathHint && (
            <div className="mt-2">
              {isHttpUrl(imagePathHint) ? (
                <button
                  type="button"
                  onClick={handleLoadImageFromUrl}
                  disabled={loadingImageUrl}
                  className="rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
                >
                  {loadingImageUrl ? "Loading..." : "Load image from URL (from Excel)"}
                </button>
              ) : (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Excel lists an image path (&quot;{imagePathHint}&quot;) that can&apos;t be loaded automatically from
                  a local file path - please upload the image manually.
                </p>
              )}
            </div>
          )}

          {imageError && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{imageError}</p>}
        </div>

        <StringListEditor label="Key Features" values={item.features} onChange={(v) => set("features", v)} />
        <StringListEditor label="Technical Specifications" values={item.specifications} onChange={(v) => set("specifications", v)} />
        <StringListEditor label="Accessories" values={item.accessories} onChange={(v) => set("accessories", v)} />

        <div className="sm:col-span-2">
          <TextField label="Installation Notes" textarea value={item.installation_notes} onChange={(v) => set("installation_notes", v)} />
        </div>
        <div className="sm:col-span-2">
          <TextField label="Additional Notes" textarea value={item.additional_notes} onChange={(v) => set("additional_notes", v)} />
        </div>
        <TextField label="Brochure (optional)" value={item.brochure_note} onChange={(v) => set("brochure_note", v)} />
      </div>

      <div className="mt-4 flex gap-3">
        <Button type="submit" disabled={!item.product_name.trim() || item.price <= 0}>
          {isEditing ? "Save Changes" : "Add Product"}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
