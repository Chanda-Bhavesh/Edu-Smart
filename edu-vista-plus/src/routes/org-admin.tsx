import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell, NAV } from "@/components/AppShell";
import { useAuth } from "@/contexts/auth";

function OrgAdminLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!loading && (!user || user.role !== "org_admin")) navigate({ to: "/login" });
  }, [user, loading, navigate]);
  if (loading || !user) return null;
  return <AppShell nav={NAV["org-admin"]}><Outlet /></AppShell>;
}

export const Route = createFileRoute("/org-admin")({ component: OrgAdminLayout });
