import { createFileRoute } from "@tanstack/react-router";
import { HostelRooms } from "@/components/hostel";

export const Route = createFileRoute("/org-admin/rooms")({ component: HostelRooms });