import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageHeader, StatCard, Card, Badge, ProgressBar, Spinner } from "@/components/AppShell";
import { adminApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/dept-admin/")({
  head: () => ({ meta: [{ title: "Dept admin dashboard · Campus OS" }] }),
  component: DeptDash,
});

function DeptDash() {
  const qc = useQueryClient();

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: adminApi.dashboard,
  });

  const { data: atRisk = [], isLoading: riskLoading } = useQuery({
    queryKey: ["at-risk"],
    queryFn: adminApi.atRiskStudents,
  });

  const { data: certs = [], isLoading: certsLoading } = useQuery({
    queryKey: ["admin-certs"],
    queryFn: adminApi.certificates,
  });

  const { data: attReport } = useQuery({
    queryKey: ["att-report"],
    queryFn: adminApi.attendanceReport,
  });

  const approve = useMutation({
    mutationFn: (id: string) => adminApi.approveCertificate(id),
    onSuccess: () => { toast.success("Approved!"); qc.invalidateQueries({ queryKey: ["admin-certs"] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const reject = useMutation({
    mutationFn: (id: string) => adminApi.rejectCertificate(id, "Rejected by admin"),
    onSuccess: () => { toast.success("Rejected."); qc.invalidateQueries({ queryKey: ["admin-certs"] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const isLoading = dashLoading || riskLoading || certsLoading;
  if (isLoading) return <Spinner />;

  const pendingCerts = certs.filter((c) => c.status === "pending" || c.status === "under_review");
  const deptAttendance = attReport?.departments ?? [];

  return (
    <>
      <PageHeader eyebrow="Department" title="Department health, this week" subtitle="Manage students, attendance, and verifications." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard tone="warm" label="Students" value={dashboard?.total_students ?? "—"} />
        <StatCard tone="cool" label="Faculty" value={dashboard?.total_faculty ?? "—"} />
        <StatCard tone="sun" label="Avg. attendance" value={`${(dashboard?.today_attendance_rate ?? 0).toFixed(1)}%`} />
        <StatCard label="Pending certs" value={dashboard?.pending_certificate_requests ?? 0} hint="Awaiting sign-off" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card title="Department attendance" className="lg:col-span-2">
          {deptAttendance.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data yet.</p>
          ) : (
            <div className="space-y-5">
              {deptAttendance.map((d) => (
                <div key={d.department}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold">{d.department}</span>
                    <span className="font-display font-semibold">{d.pct.toFixed(1)}%</span>
                  </div>
                  <div className="mt-2"><ProgressBar value={d.pct} tone={d.pct < 75 ? "warning" : "primary"} /></div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="At-risk students" action={<Link to="/dept-admin/students" className="text-sm font-semibold text-primary">All →</Link>}>
          {atRisk.length === 0 ? (
            <p className="text-sm text-muted-foreground">No at-risk students.</p>
          ) : (
            <div className="space-y-3">
              {atRisk.slice(0, 5).map((s) => (
                <div key={s.student_id} className="rounded-2xl bg-surface p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-sm">{s.student_name}</div>
                      <div className="text-xs text-muted-foreground font-mono">{s.roll_number} · {s.section}</div>
                    </div>
                    <Badge tone={s.overall_risk_level === "critical" ? "danger" : s.overall_risk_level === "high" ? "warning" : "info"}>
                      {s.overall_risk_level}
                    </Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Attendance: <span className="font-semibold text-foreground">{s.overall_attendance_pct.toFixed(1)}%</span>
                    {s.critical_subject_count > 0 && ` · ${s.critical_subject_count} critical subject(s)`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Pending certificate verifications" className="mt-6">
        {pendingCerts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No pending certificates.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="py-2">Type</th><th>Purpose</th><th>Requested</th><th>Action</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {pendingCerts.slice(0, 10).map((c) => (
                  <tr key={c.id}>
                    <td className="py-3"><Badge tone="info">{c.certificate_type}</Badge></td>
                    <td className="text-muted-foreground text-xs">{c.purpose ?? "—"}</td>
                    <td className="text-muted-foreground text-xs">{new Date(c.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="flex gap-2">
                        <button onClick={() => approve.mutate(c.id)} disabled={approve.isPending}
                          className="rounded-full bg-success/15 text-success-foreground px-3 py-1 text-xs font-semibold disabled:opacity-60">Approve</button>
                        <button onClick={() => reject.mutate(c.id)} disabled={reject.isPending}
                          className="rounded-full bg-destructive/15 text-destructive px-3 py-1 text-xs font-semibold disabled:opacity-60">Reject</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}