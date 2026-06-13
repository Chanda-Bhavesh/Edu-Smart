import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell, NAV } from "@/components/AppShell";
import { useAuth } from "@/contexts/auth";

function StudentLayout() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (!loading && (!user || user.role !== "student")) navigate({ to: "/login" });
  }, [user, loading, navigate]);
  if (loading || !user) return null;
  return <AppShell nav={NAV.student}><Outlet /></AppShell>;
}

export const Route = createFileRoute("/student")({ component: StudentLayout });
