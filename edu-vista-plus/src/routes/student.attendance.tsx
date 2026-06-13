import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, StatCard, Card, Badge, ProgressBar, Spinner } from "@/components/AppShell";
import { studentApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/student/attendance")({
  head: () => ({ meta: [{ title: "Attendance · Student · Campus OS" }] }),
  component: AttendancePage,
});

function AttendancePage() {
  const { data, isLoading } = useQuery({ queryKey: ["student-attendance"], queryFn: studentApi.attendance });
  const { data: risk } = useQuery({ queryKey: ["student-risk"], queryFn: studentApi.myRisk, retry: false });

  if (isLoading) return <Spinner />;

  const subjects = data?.subjects ?? [];
  const best = subjects.reduce((b, s) => (s.attendance_pct > (b?.attendance_pct ?? 0) ? s : b), subjects[0]);

  return (
    <>
      <PageHeader eyebrow="Attendance" title="Your attendance, by the numbers" subtitle="Subject-wise breakdown and AI risk analysis." />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard tone="warm" label="Overall" value={`${(data?.overall_pct ?? 0).toFixed(1)}%`} hint="Threshold: 75%" />
        <StatCard label="Classes attended" value={`${data?.total_present ?? 0} / ${data?.total_sessions ?? 0}`} hint="This semester" />
        <StatCard tone="success" label="Best subject" value={best?.subject_name ?? "—"} hint={best ? `${best.attendance_pct.toFixed(1)}%` : ""} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card title="Subject-wise" className="lg:col-span-2">
          {subjects.length === 0 ? (
            <p className="text-sm text-muted-foreground">No attendance records yet.</p>
          ) : (
            <div className="space-y-5">
              {subjects.map((s) => (
                <div key={s.subject_id}>
                  <div className="flex items-center justify-between text-sm">
                    <div>
                      <div className="font-semibold">{s.subject_name}</div>
                      <div className="text-xs text-muted-foreground">{s.subject_code} · {s.faculty_name}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-display font-semibold">{s.attendance_pct.toFixed(1)}%</span>
                      {s.attendance_pct < 75 && <Badge tone="warning">Below 75%</Badge>}
                    </div>
                  </div>
                  <div className="mt-2">
                    <ProgressBar value={s.attendance_pct} tone={s.attendance_pct < 75 ? "warning" : "success"} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="AI Risk Analysis">
          {risk ? (
            <div className="space-y-3">
              {risk.subject_risks.map((r) => (
                <div key={r.subject_code} className={`rounded-2xl p-3 text-sm ${
                  r.risk_level === "critical" ? "bg-destructive/10"
                  : r.risk_level === "high" ? "bg-warning/15"
                  : "bg-success/10"
                }`}>
                  <div className="font-semibold">{r.subject_name}</div>
                  <p className="text-xs text-muted-foreground mt-1">{r.recommendation}</p>
                  {!r.is_recoverable && (
                    <Badge tone="danger" >Unrecoverable</Badge>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Risk analysis unavailable.</p>
          )}
        </Card>
      </div>
    </>
  );
}
