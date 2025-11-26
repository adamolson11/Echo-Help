// frontend/src/apiConfig.ts
// Reliable API base detection for GitHub Codespaces and local dev.

export function getApiBase(): string {
  // 1. Explicit override (env var)
  const envBase = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envBase && envBase.trim().length > 0) {
    return envBase.replace(/\/$/, "");
  }

  // 2. GitHub Codespaces: frontend is on :5173, backend on :8000
  if (typeof window !== "undefined") {
    const host = window.location.host; // e.g., sturdy-thing-1234-5173.app.github.dev

    if (host.includes("app.github.dev")) {
      // Replace the frontend port (-5173) with backend port (-8000)
      return window.location.origin.replace(/-5173/i, "-8000");
    }
  }

  // 3. Local dev fallback
  return "http://127.0.0.1:8000";
}
// frontend/src/apiConfig.ts
// Shared API base URL for Search + Insights

// Default for Codespaces: replace frontend port 5173 with backend port 8000
const defaultApiBase = window.location.origin.replace("5173", "8000");

// Allow override via env var, but fall back to codespaces URL
export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  defaultApiBase;
