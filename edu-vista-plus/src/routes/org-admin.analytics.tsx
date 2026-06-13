import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, StatCard, Card, ProgressBar, Spinner } from "@/components/AppShell";
import { adminApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/org-admin/analytics")({
  head: () => ({ meta: [{ title: "Analytics · Org admin · Campus OS" }] }),
  component: Analytics,
});

function Analytics() {
  const { data: feeReport, isLoading: feeLoading } = useQuery({
    queryKey: ["fee-report"],
    queryFn: adminApi.feeReport,
  });

  const { data: attReport, isLoading: attLoading } = useQuery({
    queryKey: ["att-report"],
    queryFn: adminApi.attendanceReport,
  });

  const { data: atRisk = [], isLoading: riskLoading } = useQuery({
    queryKey: ["at-risk"],
    queryFn: adminApi.atRiskStudents,
  });

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: adminApi.dashboard,
  });

  const isLoading = feeLoading || attLoading || riskLoading || dashLoading;
  if (isLoading) return <Spinner />;

  const totalCollected = feeReport?.total_collected ?? 0;
  const totalPending = feeReport?.total_pending ?? 0;
  const feeTotal = totalCollected + totalPending;
  const feePct = feeTotal > 0 ? Math.round((totalCollected / feeTotal) * 100) : 0;
  const avgAtt = attReport?.overall_pct ?? 0;
  const criticalCount = atRisk.filter((s) => s.overall_risk_level === "critical").length;
  const highCount = atRisk.filter((s) => s.overall_risk_level === "high").length;

  const feeByType = feeReport?.collection_by_type ?? [];
  const maxFee = Math.max(...feeByType.map((f) => f.amount), 1);

  const deptAtt = [...(attReport?.departments ?? [])].sort((a, b) => b.pct - a.pct);

  return (
    <>
      <PageHeader eyebrow="Analytics" title="The numbers behind the campus" subtitle="Fee collection, attendance trends, and department performance." />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard tone="warm" label="Total students" value={dashboard?.total_students?.toLocaleString() ?? "—"} hint="Active enrollments" />
        <StatCard tone="cool" label="Fee collected" value={`₹${(totalCollected / 1e5).toFixed(1)}L`} hint={`${feePct}% of target`} />
        <StatCard tone="sun" label="Avg. attendance" value={`${avgAtt.toFixed(1)}%`} hint="Campus-wide" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card title="Fee collection by type">
          {feeByType.length === 0 ? (
            <p className="text-sm text-muted-foreground">No fee data yet.</p>
          ) : (
            <div className="flex h-48 items-end gap-3">
              {feeByType.map((f) => (
                <div key={f.fee_type} className="flex flex-1 flex-col items-center gap-2">
                  <div className="w-full rounded-t-xl bg-gradient-warm" style={{ height: `${(f.amount / maxFee) * 100}%` }} />
                  <div className="text-xs text-muted-foreground text-center truncate max-w-[80px]">{f.fee_type.replace(" Fee", "")}</div>
                  <div className="text-xs font-semibold">₹{(f.amount / 1e3).toFixed(0)}k</div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Attendance risk breakdown">
          <div className="space-y-4 text-sm">
            <div className="flex justify-between items-center">
              <div>
                <div className="font-semibold text-destructive">{criticalCount} critical</div>
                <p className="text-xs text-muted-foreground">Below 65% attendance</p>
              </div>
              <div className="text-right">
                <div className="font-semibold text-warning-foreground">{highCount} high risk</div>
                <p className="text-xs text-muted-foreground">65–75% attendance</p>
              </div>
            </div>
            <ProgressBar value={feeTotal > 0 ? Math.max(5, (atRisk.length / (dashboard?.total_students ?? 1)) * 100) : 0} tone="warning" />
            <p className="text-xs text-muted-foreground">{atRisk.length} students total at risk out of {dashboard?.total_students ?? "—"}</p>

            <div className="mt-4 space-y-2">
              {atRisk.slice(0, 5).map((s) => (
                <div key={s.student_id} className="flex items-center justify-between text-xs">
                  <span className="font-medium">{s.student_name}</span>
                  <span className={s.overall_risk_level === "critical" ? "text-destructive font-semibold" : "text-warning-foreground"}>
                    {s.overall_attendance_pct.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <Card title="Department attendance leaderboard" className="mt-6">
        {deptAtt.length === 0 ? (
          <p className="text-sm text-muted-foreground">No attendance data yet.</p>
        ) : (
          <div className="space-y-4">
            {deptAtt.map((d, i) => (
              <div key={d.department}>
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-muted-foreground w-6">#{i + 1}</span>
                    <span className="font-semibold">{d.department}</span>
                  </div>
                  <span className="font-display font-bold">{d.pct.toFixed(1)}%</span>
                </div>
                <div className="mt-2"><ProgressBar value={d.pct} tone={d.pct < 75 ? "warning" : "success"} /></div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}