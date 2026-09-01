import { vi } from "vitest";

import "@testing-library/jest-dom";

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = "";
  readonly thresholds: ReadonlyArray<number> = [];
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
} as unknown as typeof IntersectionObserver;

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock localStorage / sessionStorage.
// Sous Node >= 22 le Web Storage expérimental de Node masque celui de jsdom :
// `localStorage` existe mais n'expose ni getItem ni setItem, ce qui casse
// `shared/services/api.tsx` dès l'import. On installe une implémentation
// mémoire, indépendante de la version de Node.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

for (const name of ["localStorage", "sessionStorage"] as const) {
  Object.defineProperty(window, name, {
    value: new MemoryStorage(),
    writable: true,
    configurable: true,
  });
}

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Shims pour Radix UI sous jsdom : ces API du DOM ne sont pas implémentées,
// et sans elles les composants Select / Dialog lèvent une exception au clic.
for (const name of [
  "hasPointerCapture",
  "setPointerCapture",
  "releasePointerCapture",
  "scrollIntoView",
] as const) {
  Object.defineProperty(window.HTMLElement.prototype, name, {
    value: vi.fn(),
    writable: true,
    configurable: true,
  });
}

// Mock scrollTo
Object.defineProperty(window, "scrollTo", {
  writable: true,
  value: vi.fn(),
});
