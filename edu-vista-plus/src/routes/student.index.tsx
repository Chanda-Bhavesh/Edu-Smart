import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, StatCard, Card, Badge, ProgressBar, Spinner, ErrorMsg } from "@/components/AppShell";
import { studentApi } from "@/lib/api/endpoints";
import { useAuth } from "@/contexts/auth";

export const Route = createFileRoute("/student/")({
  head: () => ({ meta: [{ title: "Student dashboard · Campus OS" }] }),
  component: StudentDashboard,
});

function StudentDashboard() {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] ?? "there";

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["student-profile"],
    queryFn: studentApi.me,
  });

  const { data: attendance, isLoading: attLoading } = useQuery({
    queryKey: ["student-attendance"],
    queryFn: studentApi.attendance,
  });

  const { data: assignments = [], isLoading: asgLoading } = useQuery({
    queryKey: ["student-assignments"],
    queryFn: studentApi.assignments,
  });

  const { data: feeSummary, isLoading: feesLoading } = useQuery({
    queryKey: ["student-fees"],
    queryFn: studentApi.fees,
  });

  const { data: notifications = [] } = useQuery({
    queryKey: ["student-notifications"],
    queryFn: studentApi.notifications,
  });

  const { data: risk } = useQuery({
    queryKey: ["student-risk"],
    queryFn: studentApi.myRisk,
    retry: false,
  });

  const isLoading = profileLoading || attLoading || asgLoading || feesLoading;
  if (isLoading) return <Spinner />;

  const overallPct = attendance?.overall_pct ?? 0;
  const totalPending = feeSummary?.total_outstanding ?? 0;
  const upcoming = assignments.filter((a) => a.status !== "graded").slice(0, 3);
  const topSubjects = attendance?.subjects?.slice(0, 4) ?? [];
  const urgentNotifs = notifications.filter((n) => !n.is_read);

  return (
    <>
      <PageHeader
        eyebrow={`Welcome back, ${firstName}`}
        title="Here's your week at a glance"
        subtitle={`${profile?.department?.name ?? ""} · Semester ${profile?.semester?.number ?? ""} · Section ${profile?.section ?? ""}`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard tone="warm" label="Attendance" value={`${overallPct.toFixed(1)}%`} hint="Threshold 75%" />
        <StatCard tone="cool" label="Subjects" value={attendance?.subjects?.length ?? 0} hint="Enrolled this semester" />
        <StatCard tone="sun" label="Pending fees" value={`₹${(totalPending / 1000).toFixed(0)}k`} hint="Outstanding balance" />
        <StatCard label="Open tasks" value={upcoming.length} hint="Assignments pending" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card title="Subject attendance" className="lg:col-span-2" action={
          <Link to="/student/attendance" className="text-sm font-semibold text-primary">View all →</Link>
        }>
          {topSubjects.length === 0 ? (
            <p className="text-sm text-muted-foreground">No attendance records yet.</p>
          ) : (
            <div className="space-y-5">
              {topSubjects.map((s) => (
                <div key={s.subject_id}>
                  <div className="flex items-center justify-between text-sm">
                    <div>
                      <div className="font-semibold">{s.subject_name}</div>
                      <div className="text-xs text-muted-foreground">{s.subject_code} · {s.faculty_name}</div>
                    </div>
                    <div className="font-display font-semibold">{s.attendance_pct.toFixed(1)}%</div>
                  </div>
                  <div className="mt-2">
                    <ProgressBar value={s.attendance_pct} tone={s.attendance_pct < 75 ? "warning" : "primary"} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Notifications" action={
          urgentNotifs.length > 0 ? <Badge tone="info">{urgentNotifs.length} new</Badge> : undefined
        }>
          {notifications.length === 0 ? (
            <p className="text-sm text-muted-foreground">No notifications.</p>
          ) : (
            <div className="space-y-4">
              {notifications.slice(0, 4).map((n) => (
                <div key={n.id} className="flex gap-3">
                  <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${!n.is_read ? "bg-primary" : "bg-muted"}`} />
                  <div className="min-w-0">
                    <div className="font-semibold text-sm truncate">{n.title}</div>
                    <div className="text-xs text-muted-foreground line-clamp-2">{n.message}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Upcoming assignments" action={
          <Link to="/student/assignments" className="text-sm font-semibold text-primary">All →</Link>
        }>
          {upcoming.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pending assignments 🎉</p>
          ) : (
            <div className="divide-y divide-border">
              {upcoming.map((a) => (
                <div key={a.id} className="py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold truncate">{a.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {a.subject.name} · Due {new Date(a.due_date).toLocaleDateString()}
                    </div>
                  </div>
                  <Badge tone={a.my_submission ? "info" : "warning"}>
                    {a.my_submission ? "submitted" : "pending"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="AI insights" action={<Badge tone="primary">Live</Badge>}>
          {risk ? (
            <div className="space-y-3 text-sm">
              {risk.critical_subjects > 0 && (
                <div className="rounded-2xl bg-destructive/10 p-4">
                  <div className="font-semibold text-destructive">
                    {risk.critical_subjects} subject{risk.critical_subjects > 1 ? "s" : ""} at critical risk
                  </div>
                  <p className="text-muted-foreground mt-1">
                    Overall attendance: {risk.overall_attendance_pct.toFixed(1)}%
                  </p>
                </div>
              )}
              {risk.at_risk_subjects > 0 && (
                <div className="rounded-2xl bg-warning/15 p-4">
                  <div className="font-semibold text-warning-foreground">
                    {risk.at_risk_subjects} subject{risk.at_risk_subjects > 1 ? "s" : ""} below 75%
                  </div>
                  <p className="text-muted-foreground mt-1">
                    {risk.subject_risks.find((r) => r.risk_level === "high" || r.risk_level === "critical")?.recommendation}
                  </p>
                </div>
              )}
              {risk.safe_subjects > 0 && (
                <div className="rounded-2xl bg-success/15 p-4">
                  <div className="font-semibold text-success-foreground">
                    {risk.safe_subjects} subject{risk.safe_subjects > 1 ? "s" : ""} safe
                  </div>
                  <p className="text-muted-foreground mt-1">Keep attending consistently.</p>
                </div>
              )}
              <Link to="/student/chat" className="block rounded-2xl bg-info/15 p-4 hover:bg-info/25 transition">
                <div className="font-semibold text-info-foreground">Ask the AI assistant →</div>
                <p className="text-muted-foreground mt-1">Get personalised advice on attendance and performance.</p>
              </Link>
            </div>
          ) : (
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>AI insights will appear once you have attendance data.</p>
              <Link to="/student/chat" className="block rounded-2xl bg-info/15 p-4">
                <div className="font-semibold text-info-foreground">Ask the AI assistant →</div>
              </Link>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
