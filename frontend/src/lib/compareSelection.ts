import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

export const COMPARE_STORAGE_KEY = "github_weekly_project_compare_v1";
export const MAX_COMPARE_PROJECTS = 3;

export function normalizeCompareSelection(values: string[]) {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].slice(0, MAX_COMPARE_PROJECTS);
}

export function loadCompareSelection() {
  try {
    const value = JSON.parse(localStorage.getItem(COMPARE_STORAGE_KEY) || "[]");
    return Array.isArray(value) ? normalizeCompareSelection(value.map(String)) : [];
  } catch { return []; }
}

function saveCompareSelection(values: string[]) { localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(values)); }

export function useCompareSelection() {
  const [params, setParams] = useSearchParams();
  const urlSelection = normalizeCompareSelection((params.get("repos") || "").split(","));
  const [selection, setSelection] = useState<string[]>(() => urlSelection.length ? urlSelection : loadCompareSelection());

  useEffect(() => {
    if (urlSelection.length) { saveCompareSelection(urlSelection); setSelection(urlSelection); return; }
    setSelection(loadCompareSelection());
  }, [params.get("repos")]);

  function commit(next: string[]) {
    const normalized = normalizeCompareSelection(next);
    saveCompareSelection(normalized);
    setSelection(normalized);
    const nextParams = new URLSearchParams(params);
    if (normalized.length) nextParams.set("repos", normalized.join(",")); else nextParams.delete("repos");
    setParams(nextParams, { replace: true });
  }

  return {
    selection,
    isSelected: (fullName: string) => selection.includes(fullName),
    canAdd: selection.length < MAX_COMPARE_PROJECTS,
    add: (fullName: string) => commit([...selection, fullName]),
    remove: (fullName: string) => commit(selection.filter((item) => item !== fullName)),
    clear: () => commit([]),
  };
}
