import { createFileRoute } from "@tanstack/react-router";
import { HostelOutpasses } from "@/components/hostel";

export const Route = createFileRoute("/warden/outpasses")({ component: HostelOutpasses });