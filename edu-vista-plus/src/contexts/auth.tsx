import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { type AuthUser, tokens, userStore } from "@/lib/api/client";
import { authApi } from "@/lib/api/endpoints";

type AuthCtx = {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthCtx>({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => userStore.get());
  const [loading, setLoading] = useState(true);

  // On mount — verify stored token is still valid
  useEffect(() => {
    const stored = userStore.get();
    const tok = tokens.getAccess();
    if (!stored || !tok) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then((u) => {
        setUser(u);
        userStore.set(u);
      })
      .catch(() => {
        tokens.clear();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    tokens.set(data.access_token, data.refresh_token);
    userStore.set(data.user);
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokens.getRefresh();
    if (refresh) {
      try {
        await authApi.logout(refresh);
      } catch {}
    }
    tokens.clear();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

/** Map backend role → frontend route prefix */
export function roleToPath(role: AuthUser["role"]): string {
  switch (role) {
    case "student":   return "/student";
    case "faculty":   return "/faculty";
    case "dept_admin": return "/dept-admin";
    case "org_admin": return "/org-admin";
    case "warden":    return "/warden";
    default:          return "/";
  }
}
