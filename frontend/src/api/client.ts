import { API_BASE } from "../apiConfig";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

let didLogAskEchoUrl = false;

function joinUrl(base: string, path: string) {
  if (!base) return path;
  if (!path) return base;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!path.startsWith("/")) return `${base}/${path}`;
  return `${base}${path}`;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = joinUrl(API_BASE, path);
  if (import.meta.env.DEV && !didLogAskEchoUrl && path === "/api/ask-echo") {
    didLogAskEchoUrl = true;
    // eslint-disable-next-line no-console
    console.debug("Ask Echo request URL:", url);
  }
  const res = await fetch(url, init);

  // best-effort parse; some endpoints could return empty body
  let body: unknown = null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      body = await res.json();
    } catch {
      body = null;
    }
  } else {
    try {
      body = await res.text();
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    throw new ApiError(`HTTP ${res.status}`, res.status, body);
  }

  return body as T;
}

export function formatApiError(err: unknown): string {
  if (err instanceof ApiError) {
    // Prefer FastAPI's common {detail: ...} shape when available.
    const body = err.body as any;
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String(body.detail)
        : typeof err.body === "string"
          ? err.body
          : null;

    return detail ? `HTTP ${err.status}: ${detail}` : `HTTP ${err.status}`;
  }

  if (err && typeof err === "object" && "message" in (err as any)) {
    const msg = String((err as any).message || "").trim();
    if (msg) return msg;
  }

  return "Request failed";
}
