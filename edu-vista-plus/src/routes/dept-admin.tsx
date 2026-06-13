import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell, NAV } from "@/components/AppShell";
import { useAuth } from "@/contexts/auth";

function DeptAdminLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!loading && (!user || (user.role !== "dept_admin" && user.role !== "org_admin")))
      navigate({ to: "/login" });
  }, [user, loading, navigate]);
  if (loading || !user) return null;
  return <AppShell nav={NAV["dept-admin"]}><Outlet /></AppShell>;
}

export const Route = createFileRoute("/dept-admin")({ component: DeptAdminLayout });
