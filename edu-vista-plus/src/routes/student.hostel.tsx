import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader, Card, Badge, Spinner } from "@/components/AppShell";
import { studentApi, type OutpassCreate, type LeaveCreate } from "@/lib/api/endpoints";

export const Route = createFileRoute("/student/hostel")({
  head: () => ({ meta: [{ title: "Hostel · Student · Campus OS" }] }),
  component: HostelPage,
});

const STATUS_TONE = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
  checked_out: "info",
  returned: "neutral",
} as const;

function HostelPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"outpass" | "leave">("outpass");
  const [showOutpassForm, setShowOutpassForm] = useState(false);
  const [showLeaveForm, setShowLeaveForm] = useState(false);

  const [outpassForm, setOutpassForm] = useState<OutpassCreate>({
    reason: "",
    destination: "",
    contact_at_destination: "",
    from_datetime: "",
    to_datetime: "",
  });

  const today = new Date().toISOString().slice(0, 10);
  const [leaveForm, setLeaveForm] = useState<LeaveCreate>({
    reason: "",
    destination: "",
    from_date: today,
    to_date: today,
    parent_name: "",
    parent_contact: "",
    parent_relation: "",
  });

  const { data: outpasses = [], isLoading: opLoading } = useQuery({
    queryKey: ["my-outpasses"],
    queryFn: studentApi.myOutpasses,
  });

  const { data: leaves = [], isLoading: lvLoading } = useQuery({
    queryKey: ["my-leaves"],
    queryFn: studentApi.myLeaves,
  });

  const applyOutpass = useMutation({
    mutationFn: () => studentApi.applyOutpass(outpassForm),
    onSuccess: () => {
      toast.success("Outpass request submitted!");
      qc.invalidateQueries({ queryKey: ["my-outpasses"] });
      setShowOutpassForm(false);
      setOutpassForm({ reason: "", destination: "", contact_at_destination: "", from_datetime: "", to_datetime: "" });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const applyLeave = useMutation({
    mutationFn: () => studentApi.applyLeave(leaveForm),
    onSuccess: () => {
      toast.success("Leave request submitted!");
      qc.invalidateQueries({ queryKey: ["my-leaves"] });
      setShowLeaveForm(false);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const isLoading = opLoading || lvLoading;
  if (isLoading) return <Spinner />;

  return (
    <>
      <PageHeader
        eyebrow="Hostel"
        title="Outpasses & Leaves"
        subtitle="Apply for short outpasses or multi-day leaves and track your requests."
        action={
          <div className="flex gap-2">
            <button
              onClick={() => { setShowOutpassForm(true); setShowLeaveForm(false); }}
              className="rounded-full bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold"
            >
              + Outpass
            </button>
            <button
              onClick={() => { setShowLeaveForm(true); setShowOutpassForm(false); }}
              className="rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold"
            >
              + Leave
            </button>
          </div>
        }
      />

      {showOutpassForm && (
        <Card title="Apply for outpass" className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-semibold">Reason</label>
              <input value={outpassForm.reason} onChange={(e) => setOutpassForm((p) => ({ ...p, reason: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" placeholder="Medical, personal, etc." />
            </div>
            <div>
              <label className="text-sm font-semibold">Destination</label>
              <input value={outpassForm.destination} onChange={(e) => setOutpassForm((p) => ({ ...p, destination: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" placeholder="City / location" />
            </div>
            <div>
              <label className="text-sm font-semibold">From (date & time)</label>
              <input type="datetime-local" value={outpassForm.from_datetime} onChange={(e) => setOutpassForm((p) => ({ ...p, from_datetime: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-semibold">To (date & time)</label>
              <input type="datetime-local" value={outpassForm.to_datetime} onChange={(e) => setOutpassForm((p) => ({ ...p, to_datetime: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-semibold">Contact at destination</label>
              <input value={outpassForm.contact_at_destination ?? ""} onChange={(e) => setOutpassForm((p) => ({ ...p, contact_at_destination: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" placeholder="Phone number" />
            </div>
          </div>
          <div className="mt-4 flex gap-3 justify-end">
            <button onClick={() => setShowOutpassForm(false)} className="rounded-full border border-border px-4 py-2 text-sm">Cancel</button>
            <button onClick={() => applyOutpass.mutate()} disabled={applyOutpass.isPending || !outpassForm.reason || !outpassForm.destination}
              className="rounded-full bg-primary text-primary-foreground px-5 py-2 text-sm font-semibold disabled:opacity-60">
              {applyOutpass.isPending ? "Submitting…" : "Submit"}
            </button>
          </div>
        </Card>
      )}

      {showLeaveForm && (
        <Card title="Apply for leave" className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-semibold">Reason</label>
              <input value={leaveForm.reason} onChange={(e) => setLeaveForm((p) => ({ ...p, reason: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" placeholder="Family function, medical, etc." />
            </div>
            <div>
              <label className="text-sm font-semibold">Destination</label>
              <input value={leaveForm.destination} onChange={(e) => setLeaveForm((p) => ({ ...p, destination: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" placeholder="Home / city" />
            </div>
            <div>
              <label className="text-sm font-semibold">From date</label>
              <input type="date" value={leaveForm.from_date} onChange={(e) => setLeaveForm((p) => ({ ...p, from_date: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-semibold">To date</label>
              <input type="date" value={leaveForm.to_date} onChange={(e) => setLeaveForm((p) => ({ ...p, to_date: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-semibold">Parent name</label>
              <input value={leaveForm.parent_name ?? ""} onChange={(e) => setLeaveForm((p) => ({ ...p, parent_name: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-semibold">Parent contact</label>
              <input value={leaveForm.parent_contact ?? ""} onChange={(e) => setLeaveForm((p) => ({ ...p, parent_contact: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="mt-4 flex gap-3 justify-end">
            <button onClick={() => setShowLeaveForm(false)} className="rounded-full border border-border px-4 py-2 text-sm">Cancel</button>
            <button onClick={() => applyLeave.mutate()} disabled={applyLeave.isPending || !leaveForm.reason || !leaveForm.destination}
              className="rounded-full bg-primary text-primary-foreground px-5 py-2 text-sm font-semibold disabled:opacity-60">
              {applyLeave.isPending ? "Submitting…" : "Submit"}
            </button>
          </div>
        </Card>
      )}

      <div className="flex gap-2 mb-6">
        {(["outpass", "leave"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`rounded-full px-4 py-2 text-sm font-semibold capitalize ${tab === t ? "bg-primary text-primary-foreground" : "bg-card border border-border"}`}>
            {t}s ({t === "outpass" ? outpasses.length : leaves.length})
          </button>
        ))}
      </div>

      {tab === "outpass" && (
        <div className="space-y-3">
          {outpasses.length === 0 && <p className="text-sm text-muted-foreground">No outpass requests yet.</p>}
          {outpasses.map((op) => (
            <div key={op.id} className="rounded-2xl border border-border/60 bg-card p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold">{op.reason}</div>
                  <div className="text-sm text-muted-foreground mt-1">{op.destination}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {new Date(op.from_datetime).toLocaleString()} → {new Date(op.to_datetime).toLocaleString()}
                  </div>
                </div>
                <Badge tone={STATUS_TONE[op.status] ?? "neutral"}>{op.status}</Badge>
              </div>
              {op.warden_remarks && (
                <p className="mt-3 text-xs text-muted-foreground border-t border-border pt-3">
                  Warden: {op.warden_remarks}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === "leave" && (
        <div className="space-y-3">
          {leaves.length === 0 && <p className="text-sm text-muted-foreground">No leave requests yet.</p>}
          {leaves.map((lv) => (
            <div key={lv.id} className="rounded-2xl border border-border/60 bg-card p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold">{lv.reason}</div>
                  <div className="text-sm text-muted-foreground mt-1">{lv.destination}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {new Date(lv.from_date).toLocaleDateString()} → {new Date(lv.to_date).toLocaleDateString()}
                  </div>
                </div>
                <Badge tone={STATUS_TONE[lv.status] ?? "neutral"}>{lv.status}</Badge>
              </div>
              {lv.warden_remarks && (
                <p className="mt-3 text-xs text-muted-foreground border-t border-border pt-3">
                  Warden: {lv.warden_remarks}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
