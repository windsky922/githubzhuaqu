import { beforeEach, describe, expect, it } from "vitest";
import { COMPARE_STORAGE_KEY, loadCompareSelection, normalizeCompareSelection } from "./compareSelection";

describe("project comparison selection", () => {
  beforeEach(() => localStorage.clear());

  it("deduplicates and limits selections to three projects", () => {
    expect(normalizeCompareSelection(["owner/a", "owner/a", "owner/b", "owner/c", "owner/d"]))
      .toEqual(["owner/a", "owner/b", "owner/c"]);
  });

  it("loads only a valid local selection", () => {
    localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(["owner/a", "owner/b"]));
    expect(loadCompareSelection()).toEqual(["owner/a", "owner/b"]);
    localStorage.setItem(COMPARE_STORAGE_KEY, "not-json");
    expect(loadCompareSelection()).toEqual([]);
  });
});
