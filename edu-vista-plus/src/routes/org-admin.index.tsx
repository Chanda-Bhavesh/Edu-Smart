import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageHeader, StatCard, Card, Badge, ProgressBar, Spinner } from "@/components/AppShell";
import { adminApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/org-admin/")({
  head: () => ({ meta: [{ title: "Org admin dashboard · Campus OS" }] }),
  component: OrgDash,
});

function OrgDash() {
  const qc = useQueryClient();

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: adminApi.dashboard,
  });

  const { data: departments = [], isLoading: deptLoading } = useQuery({
    queryKey: ["departments"],
    queryFn: adminApi.departments,
  });

  const { data: certs = [], isLoading: certsLoading } = useQuery({
    queryKey: ["admin-certs"],
    queryFn: adminApi.certificates,
  });

  const { data: feeReport } = useQuery({
    queryKey: ["fee-report"],
    queryFn: adminApi.feeReport,
  });

  const { data: attReport } = useQuery({
    queryKey: ["att-report"],
    queryFn: adminApi.attendanceReport,
  });

  const { data: atRisk = [] } = useQuery({
    queryKey: ["at-risk"],
    queryFn: adminApi.atRiskStudents,
  });

  const { data: announcements = [] } = useQuery({
    queryKey: ["announcements"],
    queryFn: adminApi.announcements,
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

  const isLoading = dashLoading || deptLoading || certsLoading;
  if (isLoading) return <Spinner />;

  const pendingCerts = certs.filter((c) => c.status === "pending" || c.status === "under_review");
  const totalCollected = feeReport?.total_collected ?? 0;
  const totalPending = feeReport?.total_pending ?? 0;
  const feeTotal = totalCollected + totalPending;
  const feePct = feeTotal > 0 ? Math.round((totalCollected / feeTotal) * 100) : 0;

  return (
    <>
      <PageHeader
        eyebrow="Campus-wide"
        title="Your campus, in one screen"
        subtitle={`${departments.length} departments · ${dashboard?.total_students?.toLocaleString() ?? "—"} students · ${dashboard?.total_faculty ?? "—"} faculty`}
        action={<Link to="/org-admin/analytics" className="rounded-full bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold">Analytics →</Link>}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard tone="warm" label="Total students" value={dashboard?.total_students?.toLocaleString() ?? "—"} />
        <StatCard tone="cool" label="Total faculty" value={dashboard?.total_faculty ?? "—"} />
        <StatCard tone="sun" label="Avg. attendance" value={`${(dashboard?.today_attendance_rate ?? 0).toFixed(1)}%`} />
        <StatCard label="Certificates pending" value={dashboard?.pending_certificate_requests ?? 0} hint="Awaiting sign-off" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card title="Fee collection" className="lg:col-span-1">
          <div className="text-sm text-muted-foreground">This academic year</div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display text-4xl font-bold">₹{(totalCollected / 1e5).toFixed(1)}L</span>
            <span className="text-muted-foreground">/ ₹{(feeTotal / 1e5).toFixed(1)}L</span>
          </div>
          <div className="mt-4"><ProgressBar value={feePct} tone="success" /></div>
          <div className="mt-2 text-xs text-muted-foreground">{feePct}% collected</div>
        </Card>

        <Card title="Departments" className="lg:col-span-2">
          {departments.length === 0 ? (
            <p className="text-sm text-muted-foreground">No departments found.</p>
          ) : (
            <div className="space-y-3">
              {(attReport?.departments ?? []).map((d, i) => (
                <div key={i} className="flex items-center gap-4 rounded-2xl bg-surface p-4">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-warm text-primary-foreground text-sm font-bold">
                    {d.department.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold">{d.department}</div>
                    <div className="hidden sm:block mt-1 w-full">
                      <ProgressBar value={d.pct} />
                    </div>
                  </div>
                  <span className="font-display font-bold text-sm shrink-0">{d.pct.toFixed(0)}%</span>
                </div>
              ))}
              {(attReport?.departments ?? []).length === 0 && departments.map((d) => (
                <div key={d.id} className="flex items-center gap-3 rounded-2xl bg-surface p-4">
                  <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-cool font-bold text-sm">
                    {d.code}
                  </div>
                  <div className="font-semibold">{d.name}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Certificate approvals" action={<Badge tone="warning">{pendingCerts.length} pending</Badge>}>
          {pendingCerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pending certificates.</p>
          ) : (
            <div className="space-y-3">
              {pendingCerts.slice(0, 5).map((c) => (
                <div key={c.id} className="flex items-center justify-between rounded-2xl bg-surface p-3">
                  <div>
                    <div className="font-semibold text-sm">{c.certificate_type}</div>
                    <div className="text-xs text-muted-foreground">{c.purpose ?? "—"} · {new Date(c.created_at).toLocaleDateString()}</div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => approve.mutate(c.id)} disabled={approve.isPending}
                      className="rounded-full bg-success/15 text-success-foreground px-3 py-1 text-xs font-semibold disabled:opacity-60">Approve</button>
                    <button onClick={() => reject.mutate(c.id)} disabled={reject.isPending}
                      className="rounded-full bg-destructive/15 text-destructive px-3 py-1 text-xs font-semibold disabled:opacity-60">Reject</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="At-risk overview" action={<Badge tone="info">AI</Badge>}>
          <div className="space-y-3 text-sm">
            <div className="rounded-2xl bg-surface p-4">
              <div className="font-semibold">{atRisk.length} students at risk</div>
              <p className="text-xs text-muted-foreground mt-1">Based on attendance analysis across all departments.</p>
              <Link to="/org-admin/analytics" className="mt-2 inline-block text-xs font-semibold text-primary">View full report →</Link>
            </div>
            {announcements.slice(0, 3).map((a) => (
              <div key={a.id} className="rounded-2xl bg-surface p-3">
                <div className="font-semibold text-sm">{a.title}</div>
                <div className="text-xs text-muted-foreground mt-1">{a.author.full_name} · {new Date(a.created_at).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}