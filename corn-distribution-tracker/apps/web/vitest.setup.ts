import "@testing-library/jest-dom/vitest";

/**
 * Node >= 22 ships an experimental `localStorage` that can shadow jsdom's
 * implementation in Vitest (methods like getItem/clear missing). The app
 * relies on real Storage semantics for draft persistence, so install a small
 * in-memory implementation when the environment's Storage is incomplete.
 */
class MemoryStorage implements Storage {
  private readonly store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.get(String(key)) ?? null;
  }

  key(index: number): string | null {
    return [...this.store.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(String(key));
  }

  setItem(key: string, value: string): void {
    this.store.set(String(key), String(value));
  }
}

const existing = typeof window !== "undefined" ? (window.localStorage as Storage | undefined) : undefined;
if (typeof existing?.getItem !== "function" || typeof existing.clear !== "function") {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: new MemoryStorage(),
  });
}

