// frontend/src/apiConfig.ts
// Shared API base URL for Search + Insights

// Use explicit VITE_API_BASE_URL if provided, otherwise default to local backend.
// Convention A: base has no trailing /api; endpoints include /api/...
const envBase = (import.meta as any).env?.VITE_API_BASE_URL;
const rawBase = envBase && String(envBase).trim().length > 0 ? String(envBase) : "http://127.0.0.1:8001";
const normalizedBase = rawBase.replace(/\/$/, "").replace(/\/api$/, "");
export const API_BASE = normalizedBase;
