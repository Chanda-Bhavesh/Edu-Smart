import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell, NAV } from "@/components/AppShell";
import { useAuth } from "@/contexts/auth";

function WardenLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!loading && (!user || (user.role !== "warden" && user.role !== "org_admin")))
      navigate({ to: "/login" });
  }, [user, loading, navigate]);
  if (loading || !user) return null;
  return <AppShell nav={NAV.warden}><Outlet /></AppShell>;
}

export const Route = createFileRoute("/warden")({ component: WardenLayout });
