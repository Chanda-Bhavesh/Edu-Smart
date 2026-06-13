import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, StatCard, Card, Badge, Spinner } from "@/components/AppShell";
import { facultyApi, adminApi } from "@/lib/api/endpoints";
import { useAuth } from "@/contexts/auth";

export const Route = createFileRoute("/faculty/")({
  head: () => ({ meta: [{ title: "Faculty dashboard · Campus OS" }] }),
  component: FacultyDashboard,
});

function FacultyDashboard() {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["faculty-me"],
    queryFn: facultyApi.me,
  });

  const { data: slots = [], isLoading: slotsLoading } = useQuery({
    queryKey: ["timetable-today"],
    queryFn: facultyApi.timetableToday,
  });

  const { data: assignments = [], isLoading: asgLoading } = useQuery({
    queryKey: ["faculty-assignments"],
    queryFn: facultyApi.assignments,
  });

  const { data: announcements = [], isLoading: annLoading } = useQuery({
    queryKey: ["announcements"],
    queryFn: adminApi.announcements,
  });

  const isLoading = profileLoading || slotsLoading || asgLoading || annLoading;
  if (isLoading) return <Spinner />;

  const openAssignments = assignments.filter((a) => a.status === "open");
  const gradedCount = assignments.filter((a) => a.status === "graded").length;

  return (
    <>
      <PageHeader
        eyebrow={`Good morning, ${firstName}`}
        title="Your teaching dashboard"
        subtitle={`${profile?.designation ?? "Faculty"} · ${profile?.department?.name ?? ""}`}
        action={
          <Link to="/faculty/assignments" className="rounded-full bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold">
            Manage assignments →
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard tone="warm" label="Classes today" value={slots.length} hint="From timetable" />
        <StatCard tone="cool" label="Open assignments" value={openAssignments.length} hint="Awaiting submissions" />
        <StatCard tone="sun" label="Graded" value={gradedCount} hint="This semester" />
        <StatCard label="Subjects" value={new Set(assignments.map((a) => a.subject.id)).size} hint="Assigned to you" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card title="Today's classes" className="lg:col-span-2" action={
          <Link to="/faculty/attendance" className="text-sm font-semibold text-primary">Mark attendance →</Link>
        }>
          {slots.length === 0 ? (
            <p className="text-sm text-muted-foreground">No classes scheduled for today.</p>
          ) : (
            <div className="space-y-3">
              {slots.map((s) => (
                <div key={s.id} className="flex items-center gap-4 rounded-2xl bg-surface p-4">
                  <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-warm text-primary-foreground font-display font-bold text-xs text-center leading-tight">
                    {s.start_time.slice(0, 5)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold">{s.subject.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {s.room_number ?? "Room TBD"} · Sec {s.section} · Sem {s.semester_number}
                    </div>
                  </div>
                  <Link
                    to="/faculty/attendance"
                    className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-semibold"
                  >
                    Mark
                  </Link>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Recent assignments" action={
          <Badge tone="info">{openAssignments.length} open</Badge>
        }>
          {assignments.length === 0 ? (
            <p className="text-sm text-muted-foreground">No assignments yet.</p>
          ) : (
            <div className="space-y-3">
              {assignments.slice(0, 5).map((a) => (
                <div key={a.id} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-sm truncate">{a.title}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {a.subject.code} · Due {new Date(a.due_date).toLocaleDateString()}
                    </div>
                  </div>
                  <Badge tone={a.status === "graded" ? "success" : a.status === "open" ? "warning" : "neutral"}>
                    {a.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Recent announcements" className="mt-6">
        {announcements.length === 0 ? (
          <p className="text-sm text-muted-foreground">No announcements yet.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {announcements.slice(0, 4).map((a) => (
              <div key={a.id} className="rounded-2xl bg-surface p-4">
                <div className="flex items-center gap-2">
                  <div className="font-semibold text-sm">{a.title}</div>
                  {a.priority === "urgent" && <Badge tone="danger">Urgent</Badge>}
                </div>
                <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{a.content}</div>
                <div className="text-xs text-muted-foreground mt-2">
                  {a.author.full_name} · {new Date(a.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}