import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Card, PageHeader, ProgressBar, Spinner, StatCard } from "@/components/AppShell";
import { hostelApi, type VisitorCreate } from "@/lib/api/endpoints";

function useHostel() {
  const { data: hostels = [], isLoading } = useQuery({
    queryKey: ["my-hostels"],
    queryFn: hostelApi.myHostels,
  });
  const [hostelId, setHostelId] = useState<string | null>(null);
  const effectiveId = hostelId ?? hostels[0]?.id ?? null;
  return { hostels, isLoading, hostelId: effectiveId, setHostelId };
}

function HostelSelector({ hostels, hostelId, setHostelId }: {
  hostels: Array<{ id: string; name: string }>;
  hostelId: string | null;
  setHostelId: (id: string) => void;
}) {
  if (hostels.length <= 1) return null;
  return (
    <select value={hostelId ?? ""} onChange={(e) => setHostelId(e.target.value)}
      className="rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold">
      {hostels.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
    </select>
  );
}

export function HostelDashboard() {
  const { hostels, isLoading: hostelsLoading, hostelId, setHostelId } = useHostel();

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["hostel-dashboard", hostelId],
    queryFn: () => hostelApi.dashboard(hostelId!),
    enabled: !!hostelId,
  });

  if (hostelsLoading || dashLoading) return <Spinner />;

  if (!hostelId) {
    return (
      <>
        <PageHeader eyebrow="Hostel ops" title="No hostels found" subtitle="No hostels are assigned to your account." />
      </>
    );
  }

  const hostel = hostels.find((h) => h.id === hostelId);
  const occupancyPct = dashboard ? Math.round((dashboard.current_occupancy / dashboard.total_capacity) * 100) : 0;

  return (
    <>
      <PageHeader
        eyebrow="Hostel ops"
        title={`Good morning, Warden`}
        subtitle={`${hostel?.name ?? "Hostel"} · ${dashboard?.current_occupancy ?? 0} residents across ${dashboard?.total_capacity ?? 0} beds (${occupancyPct}% occupied).`}
        action={<HostelSelector hostels={hostels} hostelId={hostelId} setHostelId={setHostelId} />}
      />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Pending outpasses" value={dashboard?.pending_outpasses ?? 0} hint="Awaiting your approval" tone="warm" />
        <StatCard label="Pending leaves" value={dashboard?.pending_leaves ?? 0} hint="Multi-day requests" tone="cool" />
        <StatCard label="Visitors today" value={dashboard?.todays_visitors ?? 0} hint="Logged today" tone="sun" />
        <StatCard label="Available beds" value={dashboard?.available_beds ?? 0} hint="Unoccupied beds" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card title="Latest outpass requests" className="lg:col-span-2">
          {(dashboard?.recent_outpasses ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent outpasses.</p>
          ) : (
            <div className="divide-y divide-border/60">
              {(dashboard?.recent_outpasses ?? []).map((o) => (
                <div key={o.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div>
                    <div className="font-semibold">{o.student_name} <span className="text-muted-foreground text-sm font-normal">· {o.roll_number}</span></div>
                    <div className="text-sm text-muted-foreground">{o.reason}</div>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <div>{new Date(o.from_datetime).toLocaleDateString()} → {new Date(o.to_datetime).toLocaleDateString()}</div>
                    <Badge tone={o.status === "approved" ? "success" : o.status === "rejected" ? "danger" : "warning"}>{o.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Occupancy">
          <div className="space-y-3">
            <div>
              <div className="mb-1 flex justify-between text-sm">
                <span className="font-medium">Overall</span>
                <span className="text-muted-foreground">{occupancyPct}%</span>
              </div>
              <ProgressBar value={occupancyPct} tone={occupancyPct > 90 ? "warning" : "success"} />
            </div>
            <div className="mt-4 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Total capacity</span><span className="font-semibold">{dashboard?.total_capacity}</span></div>
              <div className="flex justify-between mt-1"><span className="text-muted-foreground">Current occupancy</span><span className="font-semibold">{dashboard?.current_occupancy}</span></div>
              <div className="flex justify-between mt-1"><span className="text-muted-foreground">Available</span><span className="font-semibold text-success-foreground">{dashboard?.available_beds}</span></div>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

export function HostelOutpasses() {
  const qc = useQueryClient();
  const { hostels, isLoading: hostelsLoading, hostelId, setHostelId } = useHostel();
  const [remarkModal, setRemarkModal] = useState<{ id: string; action: "approve" | "reject" } | null>(null);
  const [remark, setRemark] = useState("");

  const { data: outpasses = [], isLoading: opLoading } = useQuery({
    queryKey: ["hostel-outpasses", hostelId],
    queryFn: () => hostelApi.outpasses(hostelId!),
    enabled: !!hostelId,
  });

  const { data: leaves = [], isLoading: lvLoading } = useQuery({
    queryKey: ["hostel-leaves", hostelId],
    queryFn: () => hostelApi.leaves(hostelId!),
    enabled: !!hostelId,
  });

  const reviewOutpass = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      hostelApi.reviewOutpass(id, action, remark || undefined),
    onSuccess: () => {
      toast.success("Done!");
      qc.invalidateQueries({ queryKey: ["hostel-outpasses"] });
      qc.invalidateQueries({ queryKey: ["hostel-dashboard"] });
      setRemarkModal(null);
      setRemark("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const reviewLeave = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      hostelApi.reviewLeave(id, action, remark || undefined),
    onSuccess: () => {
      toast.success("Done!");
      qc.invalidateQueries({ queryKey: ["hostel-leaves"] });
      qc.invalidateQueries({ queryKey: ["hostel-dashboard"] });
      setRemarkModal(null);
      setRemark("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const checkoutOutpass = useMutation({
    mutationFn: (id: string) => hostelApi.checkoutOutpass(id),
    onSuccess: () => { toast.success("Checked out!"); qc.invalidateQueries({ queryKey: ["hostel-outpasses"] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const returnOutpass = useMutation({
    mutationFn: (id: string) => hostelApi.returnOutpass(id),
    onSuccess: () => { toast.success("Returned!"); qc.invalidateQueries({ queryKey: ["hostel-outpasses"] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (hostelsLoading || opLoading || lvLoading) return <Spinner />;

  const pendingOps = outpasses.filter((o) => o.status === "pending");
  const otherOps = outpasses.filter((o) => o.status !== "pending");
  const pendingLvs = leaves.filter((l) => l.status === "pending");
  const otherLvs = leaves.filter((l) => l.status !== "pending");

  return (
    <>
      <PageHeader eyebrow="Approvals" title="Outpasses & Leaves"
        subtitle="Approve or reject student requests."
        action={<HostelSelector hostels={hostels} hostelId={hostelId} setHostelId={setHostelId} />}
      />

      <Card title={`Outpass requests · ${pendingOps.length} pending`} className="mb-6">
        {outpasses.length === 0 ? <p className="text-sm text-muted-foreground">No outpasses.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="pb-3">Student</th><th>Reason</th><th>From → To</th><th>Status</th><th className="text-right">Action</th></tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {[...pendingOps, ...otherOps].map((o) => (
                  <tr key={o.id}>
                    <td className="py-3">
                      <div className="font-semibold">{o.student_name}</div>
                      <div className="text-xs text-muted-foreground">{o.roll_number}</div>
                    </td>
                    <td className="text-muted-foreground text-sm">{o.reason}</td>
                    <td className="text-muted-foreground whitespace-nowrap text-xs">
                      {new Date(o.from_datetime).toLocaleString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} →{" "}
                      {new Date(o.to_datetime).toLocaleString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td><Badge tone={o.status === "approved" ? "success" : o.status === "rejected" ? "danger" : o.status === "checked_out" ? "info" : "warning"}>{o.status}</Badge></td>
                    <td className="text-right">
                      <div className="inline-flex gap-2">
                        {o.status === "pending" && (
                          <>
                            <button onClick={() => { setRemarkModal({ id: o.id, action: "approve" }); }}
                              className="rounded-full bg-success/15 text-success-foreground px-3 py-1 text-xs font-semibold hover:bg-success/25">Approve</button>
                            <button onClick={() => { setRemarkModal({ id: o.id, action: "reject" }); }}
                              className="rounded-full bg-destructive/10 text-destructive px-3 py-1 text-xs font-semibold hover:bg-destructive/20">Reject</button>
                          </>
                        )}
                        {o.status === "approved" && (
                          <button onClick={() => checkoutOutpass.mutate(o.id)} disabled={checkoutOutpass.isPending}
                            className="rounded-full border border-border px-3 py-1 text-xs font-semibold">Checkout</button>
                        )}
                        {o.status === "checked_out" && (
                          <button onClick={() => returnOutpass.mutate(o.id)} disabled={returnOutpass.isPending}
                            className="rounded-full border border-border px-3 py-1 text-xs font-semibold">Return</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title={`Leave requests · ${pendingLvs.length} pending`}>
        {leaves.length === 0 ? <p className="text-sm text-muted-foreground">No leave requests.</p> : (
          <div className="divide-y divide-border/60">
            {[...pendingLvs, ...otherLvs].map((l) => (
              <div key={l.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <div className="font-semibold">{l.student_name} <span className="text-xs font-normal text-muted-foreground">· {l.roll_number}</span></div>
                  <div className="text-sm text-muted-foreground">{l.reason} · {new Date(l.from_date).toLocaleDateString()} → {new Date(l.to_date).toLocaleDateString()}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={l.status === "approved" ? "success" : l.status === "rejected" ? "danger" : "warning"}>{l.status}</Badge>
                  {l.status === "pending" && (
                    <>
                      <button onClick={() => { setRemarkModal({ id: `leave:${l.id}`, action: "approve" }); }}
                        className="rounded-full bg-success/15 text-success-foreground px-3 py-1 text-xs font-semibold">Approve</button>
                      <button onClick={() => { setRemarkModal({ id: `leave:${l.id}`, action: "reject" }); }}
                        className="rounded-full bg-destructive/10 text-destructive px-3 py-1 text-xs font-semibold">Reject</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {remarkModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur p-4">
          <div className="w-full max-w-sm rounded-3xl bg-card border border-border p-6 shadow-xl">
            <div className="font-semibold text-lg mb-4 capitalize">{remarkModal.action} request</div>
            <div>
              <label className="text-sm font-semibold">Remarks (optional)</label>
              <textarea value={remark} onChange={(e) => setRemark(e.target.value)} rows={3}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm resize-none" />
            </div>
            <div className="mt-4 flex gap-3">
              <button onClick={() => { setRemarkModal(null); setRemark(""); }} className="flex-1 rounded-full border border-border py-2 text-sm">Cancel</button>
              <button
                onClick={() => {
                  const isLeave = remarkModal.id.startsWith("leave:");
                  const realId = remarkModal.id.replace("leave:", "");
                  if (isLeave) reviewLeave.mutate({ id: realId, action: remarkModal.action });
                  else reviewOutpass.mutate({ id: realId, action: remarkModal.action });
                }}
                disabled={reviewOutpass.isPending || reviewLeave.isPending}
                className={`flex-1 rounded-full py-2 text-sm font-semibold disabled:opacity-60 ${remarkModal.action === "approve" ? "bg-success text-success-foreground" : "bg-destructive text-destructive-foreground"}`}
              >
                {reviewOutpass.isPending || reviewLeave.isPending ? "Processing…" : `Confirm ${remarkModal.action}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function HostelVisitors() {
  const qc = useQueryClient();
  const { hostels, isLoading: hostelsLoading, hostelId, setHostelId } = useHostel();
  const [form, setForm] = useState<Omit<VisitorCreate, "student_id"> & { student_id: string }>({
    student_id: "", visitor_name: "", visitor_relation: "", visitor_phone: "", visitor_id_type: "", visitor_id_number: "", purpose: "",
  });

  const { data: visitors = [], isLoading: visitorsLoading } = useQuery({
    queryKey: ["hostel-visitors", hostelId],
    queryFn: () => hostelApi.visitors(hostelId!),
    enabled: !!hostelId,
  });

  const logVisitor = useMutation({
    mutationFn: () => hostelApi.logVisitor(hostelId!, form),
    onSuccess: () => {
      toast.success("Visitor logged!");
      qc.invalidateQueries({ queryKey: ["hostel-visitors"] });
      qc.invalidateQueries({ queryKey: ["hostel-dashboard"] });
      setForm({ student_id: "", visitor_name: "", visitor_relation: "", visitor_phone: "", visitor_id_type: "", visitor_id_number: "", purpose: "" });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const checkoutVisitor = useMutation({
    mutationFn: (id: string) => hostelApi.checkoutVisitor(id),
    onSuccess: () => { toast.success("Checked out!"); qc.invalidateQueries({ queryKey: ["hostel-visitors"] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (hostelsLoading || visitorsLoading) return <Spinner />;

  const active = visitors.filter((v) => !v.check_out_time);
  const past = visitors.filter((v) => v.check_out_time);

  return (
    <>
      <PageHeader eyebrow="Front desk" title="Visitor log"
        subtitle="Quickly log who's in the hostel right now and keep a clean audit trail."
        action={<HostelSelector hostels={hostels} hostelId={hostelId} setHostelId={setHostelId} />}
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Log a visitor" className="lg:col-span-1">
          <div className="space-y-3">
            {[
              { key: "visitor_name", label: "Visitor name" },
              { key: "student_id", label: "Student ID (UUID)" },
              { key: "visitor_relation", label: "Relation" },
              { key: "visitor_phone", label: "Phone" },
              { key: "visitor_id_type", label: "ID type (Aadhar/PAN…)" },
              { key: "visitor_id_number", label: "ID number (masked)" },
              { key: "purpose", label: "Purpose of visit" },
            ].map((f) => (
              <label key={f.key} className="block text-sm">
                <span className="text-muted-foreground">{f.label}</span>
                <input
                  value={(form as Record<string, string>)[f.key]}
                  onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm"
                />
              </label>
            ))}
            <button
              onClick={() => logVisitor.mutate()}
              disabled={logVisitor.isPending || !form.visitor_name || !form.student_id}
              className="w-full rounded-full bg-primary text-primary-foreground py-2 font-semibold shadow-soft disabled:opacity-60"
            >
              {logVisitor.isPending ? "Logging…" : "Check in"}
            </button>
          </div>
        </Card>

        <Card title={`Currently inside · ${active.length}`} className="lg:col-span-2">
          <div className="divide-y divide-border/60">
            {active.length === 0 && <div className="py-6 text-center text-sm text-muted-foreground">No visitors inside right now.</div>}
            {active.map((v) => (
              <div key={v.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <div className="font-semibold">{v.visitor_name} <span className="text-xs font-normal text-muted-foreground">· {v.visitor_relation}</span></div>
                  <div className="text-sm text-muted-foreground">Visiting {v.student_name} · in at {new Date(v.check_in_time).toLocaleTimeString()}</div>
                  {v.purpose && <div className="text-xs text-muted-foreground">{v.purpose}</div>}
                </div>
                <button onClick={() => checkoutVisitor.mutate(v.id)} disabled={checkoutVisitor.isPending}
                  className="rounded-full bg-muted text-foreground px-3 py-1 text-xs font-semibold hover:bg-foreground hover:text-background disabled:opacity-60">
                  Check out
                </button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {past.length > 0 && (
        <Card title="Recent visits" className="mt-6">
          <div className="divide-y divide-border/60">
            {past.slice(0, 20).map((v) => (
              <div key={v.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
                <div>
                  <span className="font-semibold">{v.visitor_name}</span>{" "}
                  <span className="text-muted-foreground">· {v.visitor_relation} of {v.student_name}</span>
                </div>
                <div className="text-muted-foreground text-xs">
                  In: {new Date(v.check_in_time).toLocaleString()} · Out: {new Date(v.check_out_time!).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </>
  );
}

export function HostelRooms() {
  const { hostels, isLoading: hostelsLoading, hostelId, setHostelId } = useHostel();
  const [filter, setFilter] = useState<"all" | "available" | "full" | "inactive">("all");

  const { data: rooms = [], isLoading: roomsLoading } = useQuery({
    queryKey: ["hostel-rooms", hostelId],
    queryFn: () => hostelApi.rooms(hostelId!),
    enabled: !!hostelId,
  });

  const { data: allocations = [], isLoading: allocLoading } = useQuery({
    queryKey: ["hostel-allocations", hostelId],
    queryFn: () => hostelApi.allocations(hostelId!),
    enabled: !!hostelId,
  });

  if (hostelsLoading || roomsLoading || allocLoading) return <Spinner />;

  const filtered = rooms.filter((r) => {
    if (filter === "all") return true;
    if (filter === "available") return r.current_occupancy < r.capacity && r.is_active;
    if (filter === "full") return r.current_occupancy >= r.capacity;
    if (filter === "inactive") return !r.is_active;
    return true;
  });

  const roomAllocMap = allocations.reduce((acc, a) => {
    const room = a.room_number;
    if (!acc[room]) acc[room] = [];
    acc[room].push(a.student_name);
    return acc;
  }, {} as Record<string, string[]>);

  return (
    <>
      <PageHeader eyebrow="Allocations" title="Room management"
        subtitle="See live occupancy across all rooms. Manage beds and allocations."
        action={
          <div className="flex flex-wrap gap-2 items-center">
            <HostelSelector hostels={hostels} hostelId={hostelId} setHostelId={setHostelId} />
            <div className="flex flex-wrap gap-1.5 text-xs font-semibold">
              {(["all", "available", "full", "inactive"] as const).map((f) => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`rounded-full px-3 py-1.5 capitalize border ${filter === f ? "bg-primary text-primary-foreground border-primary" : "bg-card border-border text-muted-foreground"}`}>
                  {f}
                </button>
              ))}
            </div>
          </div>
        }
      />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((r) => {
          const pct = Math.round((r.current_occupancy / r.capacity) * 100);
          const residents = roomAllocMap[r.room_number] ?? [];
          const statusTone = !r.is_active ? "danger" : r.current_occupancy >= r.capacity ? "success" : r.current_occupancy > 0 ? "warning" : "info";
          const statusLabel = !r.is_active ? "inactive" : r.current_occupancy >= r.capacity ? "full" : r.current_occupancy > 0 ? "partial" : "vacant";
          return (
            <div key={r.id} className="rounded-3xl border border-border/60 bg-card p-5 shadow-soft">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-display text-2xl font-bold">{r.room_number}</div>
                  <div className="text-xs text-muted-foreground">Floor {r.floor} · {r.current_occupancy}/{r.capacity} beds · {r.room_type}</div>
                </div>
                <Badge tone={statusTone}>{statusLabel}</Badge>
              </div>
              <div className="mt-4">
                <ProgressBar value={pct} tone={pct >= 100 ? "success" : pct > 50 ? "warning" : "primary"} />
              </div>
              <div className="mt-3 text-sm text-muted-foreground">
                {residents.length > 0 ? residents.join(", ") : "Vacant"}
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="col-span-3 py-12 text-center text-muted-foreground text-sm">No rooms match the filter.</div>
        )}
      </div>
    </>
  );
}
