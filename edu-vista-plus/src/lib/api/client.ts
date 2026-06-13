export const BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  "http://localhost:8000/api/v1";

const isBrowser = typeof window !== "undefined";

// ── Token storage ──────────────────────────────────────────────────────────────
export const tokens = {
  getAccess: () => isBrowser ? localStorage.getItem("access_token") : null,
  getRefresh: () => isBrowser ? localStorage.getItem("refresh_token") : null,
  set: (access: string, refresh: string) => {
    if (!isBrowser) return;
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  },
  clear: () => {
    if (!isBrowser) return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("scms_user");
  },
};

// ── User storage ───────────────────────────────────────────────────────────────
export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: "student" | "faculty" | "dept_admin" | "org_admin" | "warden";
  is_active: boolean;
};

export const userStore = {
  get: (): AuthUser | null => {
    if (!isBrowser) return null;
    try {
      const raw = localStorage.getItem("scms_user");
      if (!raw || raw === "undefined" || raw === "null") {
        localStorage.removeItem("scms_user");
        return null;
      }
      return JSON.parse(raw) as AuthUser;
    } catch {
      localStorage.removeItem("scms_user");
      return null;
    }
  },
  set: (u: AuthUser) => {
    if (!isBrowser || !u) return;
    localStorage.setItem("scms_user", JSON.stringify(u));
  },
  clear: () => { if (isBrowser) localStorage.removeItem("scms_user"); },
};

// ── Core fetch wrapper ─────────────────────────────────────────────────────────
let _refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = (async () => {
    const refresh = tokens.getRefresh();
    if (!refresh) return false;
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      tokens.set(data.access_token, data.refresh_token ?? refresh);
      return true;
    } catch {
      return false;
    } finally {
      _refreshPromise = null;
    }
  })();
  return _refreshPromise;
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit & { skipAuth?: boolean } = {},
): Promise<T> {
  const { skipAuth, ...rest } = init;

  const makeHeaders = (): HeadersInit => {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      ...(rest.headers as Record<string, string>),
    };
    if (!skipAuth) {
      const tok = tokens.getAccess();
      if (tok) h["Authorization"] = `Bearer ${tok}`;
    }
    return h;
  };

  let res = await fetch(`${BASE}${path}`, { ...rest, headers: makeHeaders() });

  // Token expired — try refresh once
  if (res.status === 401 && !skipAuth) {
    const ok = await tryRefresh();
    if (ok) {
      res = await fetch(`${BASE}${path}`, { ...rest, headers: makeHeaders() });
    } else {
      tokens.clear();
      if (isBrowser) window.location.href = "/login";
      throw new Error("Session expired");
    }
  }

  if (!res.ok) {
    let msg = `API error ${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail ?? msg;
    } catch {}
    throw new Error(msg);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ── Convenience methods ────────────────────────────────────────────────────────
export const api = {
  get: <T>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { method: "GET", ...opts }),

  post: <T>(path: string, body?: unknown, opts?: RequestInit) =>
    apiFetch<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  patch: <T>(path: string, body?: unknown, opts?: RequestInit) =>
    apiFetch<T>(path, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  put: <T>(path: string, body?: unknown, opts?: RequestInit) =>
    apiFetch<T>(path, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  delete: <T>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { method: "DELETE", ...opts }),

  // Multipart upload (assignments, etc.)
  upload: <T>(path: string, formData: FormData) =>
    apiFetch<T>(path, {
      method: "POST",
      body: formData,
      headers: {}, // let browser set Content-Type with boundary
    }),
};
