// frontend/src/apiConfig.ts
// Shared API base URL for Search + Insights

// Use explicit VITE_API_BASE_URL if provided, otherwise default to a relative
// base so `fetch('/api/...')` will go through Vite's proxy/local origin.
const envBase = (import.meta as any).env?.VITE_API_BASE_URL;
const rawBase = envBase && String(envBase).trim().length > 0 ? String(envBase) : "";
const normalizedBase = rawBase.replace(/\/$/, "").replace(/\/api$/, "");
export const API_BASE = normalizedBase;
