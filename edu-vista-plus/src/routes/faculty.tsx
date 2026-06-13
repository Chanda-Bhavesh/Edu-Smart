import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell, NAV } from "@/components/AppShell";
import { useAuth } from "@/contexts/auth";

function FacultyLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!loading && (!user || user.role !== "faculty")) navigate({ to: "/login" });
  }, [user, loading, navigate]);
  if (loading || !user) return null;
  return <AppShell nav={NAV.faculty}><Outlet /></AppShell>;
}

export const Route = createFileRoute("/faculty")({ component: FacultyLayout });
