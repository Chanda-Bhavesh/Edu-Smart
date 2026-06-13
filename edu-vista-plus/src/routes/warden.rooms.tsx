import { createFileRoute } from "@tanstack/react-router";
import { HostelRooms } from "@/components/hostel";

export const Route = createFileRoute("/warden/rooms")({ component: HostelRooms });