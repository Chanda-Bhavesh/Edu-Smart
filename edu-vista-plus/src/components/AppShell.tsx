import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { type ReactNode } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth";
import type { AuthUser } from "@/lib/api/client";

export type NavItem = { to: string; label: string; icon: string };

const ROLE_LABEL: Record<AuthUser["role"], string> = {
  student: "Student",
  faculty: "Faculty",
  dept_admin: "Dept Admin",
  org_admin: "Org Admin",
  warden: "Warden",
};

const ROLE_EMOJI: Record<AuthUser["role"], string> = {
  student: "🎒",
  faculty: "📚",
  dept_admin: "🏛️",
  org_admin: "🌐",
  warden: "🛏️",
};

function useTodayLabel() {
  const now = new Date();
  return now.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

export function AppShell({ nav, children }: { nav: NavItem[]; children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const today = useTodayLabel();

  const role = user?.role ?? "student";
  const emoji = ROLE_EMOJI[role];
  const title = ROLE_LABEL[role];
  const name = user?.full_name ?? "—";

  async function handleLogout() {
    await logout();
    toast.success("Signed out");
    navigate({ to: "/login" });
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex">
        <aside className="hidden lg:flex w-72 shrink-0 flex-col gap-6 border-r border-border bg-sidebar p-6 sticky top-0 h-screen">
          <Link to="/" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-warm text-primary-foreground text-lg shadow-soft">
              ✦
            </span>
            <div>
              <div className="font-display text-lg font-bold leading-none">Campus OS</div>
              <div className="text-xs text-muted-foreground mt-1">Smart Campus Suite</div>
            </div>
          </Link>

          <div className="rounded-2xl bg-sidebar-accent p-4">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-cool text-xl">{emoji}</div>
              <div className="min-w-0">
                <div className="font-semibold truncate">{name}</div>
                <div className="text-xs text-muted-foreground truncate">{title}</div>
              </div>
            </div>
          </div>

          <nav className="flex flex-col gap-1">
            {nav.map((item) => {
              const active = pathname === item.to || (item.to.length > 1 && pathname.startsWith(item.to + "/"));
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary text-primary-foreground shadow-soft"
                      : "text-sidebar-foreground hover:bg-sidebar-accent",
                  )}
                >
                  <span className="text-base">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto space-y-2">
            <button
              onClick={handleLogout}
              className="w-full rounded-xl border border-border bg-card px-3 py-2.5 text-sm font-medium text-muted-foreground hover:text-destructive hover:border-destructive/40 transition-colors text-left flex items-center gap-3"
            >
              <span>🚪</span> Sign out
            </button>
          </div>
        </aside>

        <main className="flex-1 min-w-0">
          <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-border bg-background/80 px-4 py-3 backdrop-blur lg:px-10">
            <div className="flex items-center gap-3 lg:hidden">
              <Link to="/" className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-warm text-primary-foreground">
                ✦
              </Link>
              <span className="font-display font-bold">Campus OS</span>
            </div>
            <div className="hidden lg:flex items-center gap-2 text-sm text-muted-foreground">
              <span className="rounded-full bg-muted px-3 py-1 font-medium text-foreground">{title} workspace</span>
              <span>·</span>
              <span>{today}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-gradient-cool text-sm font-semibold">
                {name.split(" ").map((p) => p[0]).slice(0, 2).join("")}
              </div>
              <button
                onClick={handleLogout}
                className="hidden md:inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground hover:text-destructive hover:border-destructive/40 transition-colors"
              >
                🚪 Sign out
              </button>
            </div>
          </header>

          <div className="px-4 py-6 lg:px-10 lg:py-10 max-w-[1400px] mx-auto">
            {/* mobile nav */}
            <nav className="mb-6 flex gap-2 overflow-x-auto pb-2 lg:hidden">
              {nav.map((item) => {
                const active = pathname === item.to;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={cn(
                      "shrink-0 rounded-full px-4 py-2 text-sm font-medium",
                      active ? "bg-primary text-primary-foreground" : "bg-card border border-border text-foreground",
                    )}
                  >
                    {item.icon} {item.label}
                  </Link>
                );
              })}
            </nav>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <div className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">{eyebrow}</div>}
        <h1 className="mt-1 text-3xl lg:text-4xl font-bold">{title}</h1>
        {subtitle && <p className="mt-2 text-muted-foreground max-w-2xl">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "warm" | "cool" | "sun" | "success";
}) {
  const toneClass =
    tone === "warm" ? "bg-gradient-warm text-primary-foreground"
    : tone === "cool" ? "bg-gradient-cool"
    : tone === "sun" ? "bg-gradient-sun text-accent-foreground"
    : tone === "success" ? "bg-success/15 text-success-foreground"
    : "bg-card";
  return (
    <div className={cn("rounded-3xl p-5 shadow-soft border border-border/40", toneClass)}>
      <div className="text-xs font-semibold uppercase tracking-wider opacity-80">{label}</div>
      <div className="mt-2 text-3xl font-bold font-display">{value}</div>
      {hint && <div className="mt-1 text-sm opacity-80">{hint}</div>}
    </div>
  );
}

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-3xl bg-card border border-border/60 p-6 shadow-soft", className)}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-lg font-semibold font-display">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger" | "info" | "primary";
}) {
  const cls =
    tone === "success" ? "bg-success/15 text-success-foreground"
    : tone === "warning" ? "bg-warning/20 text-warning-foreground"
    : tone === "danger" ? "bg-destructive/15 text-destructive"
    : tone === "info" ? "bg-info/15 text-info-foreground"
    : tone === "primary" ? "bg-primary/15 text-primary"
    : "bg-muted text-muted-foreground";
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", cls)}>
      {children}
    </span>
  );
}

export function ProgressBar({
  value,
  tone = "primary",
}: {
  value: number;
  tone?: "primary" | "success" | "warning" | "danger";
}) {
  const cls =
    tone === "success" ? "bg-success"
    : tone === "warning" ? "bg-warning"
    : tone === "danger" ? "bg-destructive"
    : "bg-primary";
  return (
    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
      <div
        className={cn("h-full rounded-full transition-all", cls)}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center py-12 text-muted-foreground", className)}>
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
    </div>
  );
}

export function ErrorMsg({ message }: { message: string }) {
  return (
    <div className="rounded-2xl bg-destructive/10 text-destructive px-4 py-3 text-sm font-medium">
      {message}
    </div>
  );
}

// role-based nav definitions (kept here so AppShell + routes can share)
export const NAV = {
  student: [
    { to: "/student", label: "Dashboard", icon: "🏠" },
    { to: "/student/attendance", label: "Attendance", icon: "📅" },
    { to: "/student/assignments", label: "Assignments", icon: "📝" },
    { to: "/student/fees", label: "Fees", icon: "💳" },
    { to: "/student/certificates", label: "Certificates", icon: "📜" },
    { to: "/student/hostel", label: "Hostel", icon: "🏠" },
    { to: "/student/chat", label: "AI Assistant", icon: "🤖" },
  ],
  faculty: [
    { to: "/faculty", label: "Dashboard", icon: "🏠" },
    { to: "/faculty/attendance", label: "Mark Attendance", icon: "✅" },
    { to: "/faculty/assignments", label: "Assignments", icon: "📝" },
  ],
  "dept-admin": [
    { to: "/dept-admin", label: "Dashboard", icon: "🏠" },
    { to: "/dept-admin/students", label: "Students", icon: "🎓" },
  ],
  "org-admin": [
    { to: "/org-admin", label: "Dashboard", icon: "🏠" },
    { to: "/org-admin/analytics", label: "Analytics", icon: "📊" },
    { to: "/org-admin/outpasses", label: "Outpasses", icon: "🪪" },
    { to: "/org-admin/visitors", label: "Visitors", icon: "👋" },
    { to: "/org-admin/rooms", label: "Rooms", icon: "🛏️" },
  ],
  warden: [
    { to: "/warden", label: "Dashboard", icon: "🏠" },
    { to: "/warden/outpasses", label: "Outpasses & Leaves", icon: "🪪" },
    { to: "/warden/visitors", label: "Visitors", icon: "👋" },
    { to: "/warden/rooms", label: "Rooms", icon: "🛏️" },
  ],
} satisfies Record<string, NavItem[]>;
