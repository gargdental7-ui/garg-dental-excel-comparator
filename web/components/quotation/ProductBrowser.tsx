"use client";

import { useMemo, useState } from "react";
import type { QuotationImportedProduct } from "@/lib/types";

const PAGE_SIZE = 50;
type SortKey = "name_asc" | "name_desc" | "price_asc" | "price_desc";

function fmt(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function ProductBrowser({
  products,
  fileName,
  onSelect,
}: {
  products: QuotationImportedProduct[];
  fileName: string;
  onSelect: (product: QuotationImportedProduct) => void;
}) {
  const [search, setSearch] = useState("");
  const [brand, setBrand] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<SortKey>("name_asc");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const brands = useMemo(
    () => Array.from(new Set(products.map((p) => p.brand).filter(Boolean))).sort(),
    [products],
  );
  const categories = useMemo(
    () => Array.from(new Set(products.map((p) => p.category).filter(Boolean))).sort(),
    [products],
  );

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    let result = products.filter((p) => {
      if (brand && p.brand !== brand) return false;
      if (category && p.category !== category) return false;
      if (!query) return true;
      return (
        p.product_name.toLowerCase().includes(query) ||
        p.code.toLowerCase().includes(query) ||
        p.brand.toLowerCase().includes(query) ||
        p.model.toLowerCase().includes(query) ||
        p.category.toLowerCase().includes(query)
      );
    });
    result = [...result].sort((a, b) => {
      switch (sort) {
        case "name_asc":
          return a.product_name.localeCompare(b.product_name);
        case "name_desc":
          return b.product_name.localeCompare(a.product_name);
        case "price_asc":
          return a.price - b.price;
        case "price_desc":
          return b.price - a.price;
      }
    });
    return result;
  }, [products, search, brand, category, sort]);

  const visible = filtered.slice(0, visibleCount);

  function resetPaging() {
    setVisibleCount(PAGE_SIZE);
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
        Browse Products <span className="font-normal text-slate-500 dark:text-slate-400">({fileName})</span>
      </p>

      <div className="mb-3 flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Search name, code, brand, model, category..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            resetPaging();
          }}
          className="min-w-[220px] flex-1 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm text-slate-900 dark:text-slate-100"
        />
        {brands.length > 0 && (
          <select
            value={brand}
            onChange={(e) => {
              setBrand(e.target.value);
              resetPaging();
            }}
            className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm"
          >
            <option value="">All Brands</option>
            {brands.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        )}
        {categories.length > 0 && (
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              resetPaging();
            }}
            className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        )}
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
          className="rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1.5 text-sm"
        >
          <option value="name_asc">Name (A-Z)</option>
          <option value="name_desc">Name (Z-A)</option>
          <option value="price_asc">Price (Low-High)</option>
          <option value="price_desc">Price (High-Low)</option>
        </select>
      </div>

      <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
        {filtered.length.toLocaleString()} of {products.length.toLocaleString()} products
      </p>

      <div className="max-h-96 overflow-y-auto rounded-md border border-slate-200 dark:border-slate-800">
        {visible.length === 0 ? (
          <p className="p-4 text-sm text-slate-500 dark:text-slate-400">No products match your search.</p>
        ) : (
          <ul className="divide-y divide-slate-200 dark:divide-slate-800">
            {visible.map((p, i) => (
              <li key={`${p.code}-${p.product_name}-${i}`} className="flex items-center justify-between gap-3 p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-50">{p.product_name}</p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {[p.brand, p.model, p.category].filter(Boolean).join(" · ") || " "}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-sm text-slate-700 dark:text-slate-300">{fmt(p.price)}</span>
                  <button
                    type="button"
                    onClick={() => onSelect(p)}
                    className="rounded-md border border-slate-300 dark:border-slate-700 px-3 py-1 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    Select
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {visibleCount < filtered.length && (
        <button
          type="button"
          onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
          className="mt-3 text-sm font-medium text-slate-700 dark:text-slate-300 hover:underline"
        >
          Show more ({filtered.length - visibleCount} remaining)
        </button>
      )}
    </div>
  );
}
