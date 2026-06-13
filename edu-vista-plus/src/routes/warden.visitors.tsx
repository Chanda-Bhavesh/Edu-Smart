import { createFileRoute } from "@tanstack/react-router";
import { HostelVisitors } from "@/components/hostel";

export const Route = createFileRoute("/warden/visitors")({ component: HostelVisitors });