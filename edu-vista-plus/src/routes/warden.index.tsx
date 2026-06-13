import { createFileRoute } from "@tanstack/react-router";
import { HostelDashboard } from "@/components/hostel";

export const Route = createFileRoute("/warden/")({ component: HostelDashboard });