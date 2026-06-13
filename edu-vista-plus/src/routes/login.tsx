import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth, roleToPath } from "@/contexts/auth";

export const Route = createFileRoute("/login")({
  head: () => ({ meta: [{ title: "Sign in · Campus OS" }] }),
  component: LoginPage,
});

function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Already logged in
  if (user) {
    navigate({ to: roleToPath(user.role) });
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      const u = JSON.parse(localStorage.getItem("scms_user") ?? "{}");
      navigate({ to: roleToPath(u.role) });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-10 justify-center">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-warm text-primary-foreground text-xl shadow-soft">
            ✦
          </span>
          <div>
            <div className="font-display text-2xl font-bold leading-none">Campus OS</div>
            <div className="text-xs text-muted-foreground mt-1">Smart Campus Management</div>
          </div>
        </div>

        <div className="rounded-3xl border border-border bg-card p-8 shadow-soft">
          <h1 className="text-2xl font-bold font-display mb-1">Welcome back</h1>
          <p className="text-muted-foreground text-sm mb-6">Sign in to your campus account</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5" htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@campus.edu"
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
              />
            </div>

            {error && (
              <div className="rounded-xl bg-destructive/10 text-destructive px-4 py-3 text-sm font-medium">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-primary text-primary-foreground px-4 py-2.5 text-sm font-semibold shadow-soft disabled:opacity-60 hover:opacity-90 transition"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Contact your administrator if you need account access.
        </p>
      </div>
    </div>
  );
}
