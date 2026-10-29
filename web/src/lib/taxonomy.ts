"use client";

import { useEffect, useState } from "react";

export interface TaxItem {
  id: string;
  label: string;
  group: string;
  hint: string;
  count: number;
}

export interface TaxDimension {
  entity: string;
  catch_all: string | null;
  items: TaxItem[];
  unlisted_values: string[];
}

export type Taxonomy = Record<string, TaxDimension>;

let cached: Promise<Taxonomy> | null = null;

/** The static classifications (`kb taxonomy`): fixed lists with counts, `other` as the catch-all. Loaded once per page load. */
export function loadTaxonomy(): Promise<Taxonomy> {
  if (!cached) {
    cached = fetch("/api/taxonomy")
      .then((r) => r.json())
      .then((r) => (r.ok ? (r.taxonomy as Taxonomy) : Promise.reject(new Error(r.error || "taxonomy"))))
      .catch((e) => {
        cached = null;
        throw e;
      });
  }
  return cached;
}

export function useTaxonomy(): Taxonomy | null {
  const [t, setT] = useState<Taxonomy | null>(null);
  useEffect(() => {
    let live = true;
    loadTaxonomy().then((x) => live && setT(x)).catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);
  return t;
}

export function labelOf(t: Taxonomy | null, dim: string, id?: string | null): string {
  if (!id) return "";
  return t?.[dim]?.items.find((i) => i.id === id)?.label || id.replace(/_/g, " ");
}
