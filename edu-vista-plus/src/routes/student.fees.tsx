import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader, StatCard, Card, Badge, ProgressBar, Spinner } from "@/components/AppShell";
import { studentApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/student/fees")({
  head: () => ({ meta: [{ title: "Fees · Student · Campus OS" }] }),
  component: FeesPage,
});

function FeesPage() {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["student-fees"],
    queryFn: studentApi.fees,
  });

  const { data: payments = [] } = useQuery({
    queryKey: ["fee-payments", expandedId],
    queryFn: () => studentApi.feePayments(expandedId!),
    enabled: !!expandedId,
  });

  if (isLoading) return <Spinner />;

  const fees = summary?.fees ?? [];
  const totalPaid = summary?.total_paid_ever ?? 0;
  const totalOutstanding = summary?.total_outstanding ?? 0;
  const grandTotal = totalPaid + totalOutstanding;
  const pct = grandTotal > 0 ? Math.round((totalPaid / grandTotal) * 100) : 0;

  const nextDue = fees.filter((f) => f.balance > 0).sort(
    (a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
  )[0];

  return (
    <>
      <PageHeader
        eyebrow="Fees"
        title="Fee summary"
        subtitle={nextDue
          ? `Next due: ₹${nextDue.balance.toLocaleString()} by ${new Date(nextDue.due_date).toLocaleDateString()}`
          : fees.length > 0 ? "All fees paid!" : "No fee records yet."}
        action={
          totalOutstanding > 0 ? (
            <button
              onClick={() => toast.info("Online payment integration coming soon. Please visit the accounts office.")}
              className="rounded-full bg-primary text-primary-foreground px-5 py-2.5 text-sm font-semibold shadow-soft"
            >
              Pay ₹{totalOutstanding.toLocaleString()}
            </button>
          ) : undefined
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard tone="warm" label="Total billed" value={`₹${grandTotal.toLocaleString()}`} />
        <StatCard tone="success" label="Paid" value={`₹${totalPaid.toLocaleString()}`} hint={`${pct}% complete`} />
        <StatCard tone="sun" label="Outstanding" value={`₹${totalOutstanding.toLocaleString()}`} />
      </div>

      <Card title="Fee records" className="mt-6">
        <ProgressBar value={pct} tone="success" />
        <div className="mt-2 text-sm text-muted-foreground">{pct}% paid · ₹{totalOutstanding.toLocaleString()} remaining</div>

        <div className="mt-6 space-y-3">
          {fees.length === 0 && <p className="text-sm text-muted-foreground">No fee records found.</p>}
          {fees.map((f) => {
            const label = f.academic_year
              ? `${f.academic_year} · Sem ${f.semester_number ?? "—"}`
              : `Semester ${f.semester_number ?? "—"}`;
            const isExpanded = expandedId === f.id;

            return (
              <div key={f.id} className="rounded-2xl border border-border bg-surface overflow-hidden">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : f.id)}
                  className="w-full text-left p-4 flex items-center justify-between gap-3"
                >
                  <div>
                    <div className="font-semibold text-sm">{label} {f.department_name ? `· ${f.department_name}` : ""}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      Due {new Date(f.due_date).toLocaleDateString()}
                      {f.waiver_reason && ` · Waiver applied`}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge tone={f.status === "paid" ? "success" : f.status === "overdue" ? "danger" : "warning"}>
                      {f.status}
                    </Badge>
                    <div className="text-right text-sm">
                      <div className="font-semibold">₹{f.amount_paid.toLocaleString()} paid</div>
                      {f.balance > 0 && <div className="text-xs text-muted-foreground">₹{f.balance.toLocaleString()} due</div>}
                    </div>
                    <span className="text-muted-foreground">{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </button>

                {isExpanded && (
                  <div className="border-t border-border p-4">
                    <div className="grid gap-2 sm:grid-cols-2 text-sm">
                      {[
                        { label: "Total billed", value: f.net_amount },
                        { label: "Paid", value: f.amount_paid },
                        { label: "Balance", value: f.balance },
                        ...(f.fine_amount > 0 ? [{ label: "Late fine", value: f.fine_amount }] : []),
                        ...(f.discount_amount > 0 ? [{ label: "Discount", value: f.discount_amount }] : []),
                      ].map((r) => (
                        <div key={r.label} className="flex justify-between">
                          <span className="text-muted-foreground">{r.label}</span>
                          <span className="font-semibold">₹{r.value.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>

                    {[
                      { key: "tuition_fee", label: "Tuition" },
                      { key: "exam_fee", label: "Exam" },
                      { key: "library_fee", label: "Library" },
                      { key: "lab_fee", label: "Lab" },
                      { key: "other_fee", label: "Other" },
                    ].filter((c) => (f as Record<string, unknown>)[c.key] != null && (f as Record<string, unknown>)[c.key] !== 0).length > 0 && (
                      <div className="mt-4 border-t border-border pt-3">
                        <div className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">Breakdown</div>
                        <div className="grid gap-1.5 sm:grid-cols-2 text-sm">
                          {([
                            { key: "tuition_fee" as const, label: "Tuition" },
                            { key: "exam_fee" as const, label: "Exam" },
                            { key: "library_fee" as const, label: "Library" },
                            { key: "lab_fee" as const, label: "Lab" },
                            { key: "other_fee" as const, label: "Other" },
                          ] as const).filter((c) => f[c.key] != null && f[c.key] !== 0).map((c) => (
                            <div key={c.key} className="flex justify-between">
                              <span className="text-muted-foreground">{c.label}</span>
                              <span>₹{(f[c.key] ?? 0).toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-4 border-t border-border pt-3">
                      <div className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">Payment history</div>
                      {payments.length === 0 ? (
                        <p className="text-xs text-muted-foreground">No payments recorded yet.</p>
                      ) : (
                        <div className="space-y-2">
                          {payments.map((p) => (
                            <div key={p.id} className="flex items-center justify-between text-sm">
                              <div>
                                <span className="font-semibold">₹{p.amount.toLocaleString()}</span>
                                <span className="text-muted-foreground text-xs ml-2">{p.payment_mode} · {new Date(p.payment_date).toLocaleDateString()}</span>
                              </div>
                              <a href={studentApi.downloadReceipt(p.id)} target="_blank" rel="noopener noreferrer"
                                className="text-xs font-semibold text-primary">Receipt</a>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </>
  );
}
