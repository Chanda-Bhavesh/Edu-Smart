import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { PageHeader, Card, Badge, Spinner } from "@/components/AppShell";
import { facultyApi, type AttendanceRecord, type StudentInClass } from "@/lib/api/endpoints";

export const Route = createFileRoute("/faculty/attendance")({
  head: () => ({ meta: [{ title: "Mark attendance · Faculty · Campus OS" }] }),
  component: MarkAttendance,
});

type Status = "present" | "absent" | "late" | "medical";
const STATUS_KEYS: { key: Status; label: string; short: string }[] = [
  { key: "present", label: "Present", short: "P" },
  { key: "absent", label: "Absent", short: "A" },
  { key: "late", label: "Late", short: "L" },
  { key: "medical", label: "Medical", short: "M" },
];

function MarkAttendance() {
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [roster, setRoster] = useState<Record<string, Status>>({});
  const today = new Date().toISOString().slice(0, 10);

  const { data: slots = [], isLoading: slotsLoading } = useQuery({
    queryKey: ["timetable-today"],
    queryFn: facultyApi.timetableToday,
  });

  const selectedSlot = slots.find((s) => s.id === selectedSlotId) ?? slots[0] ?? null;
  const effectiveSlotId = selectedSlotId ?? selectedSlot?.id ?? null;

  const { data: students = [], isLoading: studentsLoading } = useQuery({
    queryKey: ["slot-students", effectiveSlotId],
    queryFn: () => facultyApi.getStudentsForSlot(selectedSlot!.course_assignment_id),
    enabled: !!selectedSlot,
  });

  useEffect(() => {
    if (students.length > 0) {
      setRoster(Object.fromEntries(students.map((s) => [s.id, "present" as Status])));
    }
  }, [students]);

  const save = useMutation({
    mutationFn: () => {
      const records: AttendanceRecord[] = students.map((s) => ({
        student_id: s.id,
        status: roster[s.id] ?? "absent",
      }));
      return facultyApi.markBulkAttendance(effectiveSlotId!, today, records);
    },
    onSuccess: () => toast.success("Attendance saved!"),
    onError: (e: Error) => toast.error(e.message),
  });

  if (slotsLoading) return <Spinner />;

  if (slots.length === 0) {
    return (
      <>
        <PageHeader eyebrow="Mark attendance" title="No classes today" subtitle="You have no classes scheduled for today." />
      </>
    );
  }

  const counts = STATUS_KEYS.map((k) => ({
    ...k,
    count: Object.values(roster).filter((v) => v === k.key).length,
  }));

  return (
    <>
      <PageHeader
        eyebrow="Mark attendance"
        title={selectedSlot ? `${selectedSlot.subject.name} · ${selectedSlot.section}` : "Select a class"}
        subtitle={selectedSlot ? `${today} · ${selectedSlot.start_time.slice(0, 5)} slot · ${students.length} students` : ""}
        action={
          <div className="flex gap-2">
            {slots.length > 1 && (
              <select
                value={effectiveSlotId ?? ""}
                onChange={(e) => setSelectedSlotId(e.target.value)}
                className="rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold"
              >
                {slots.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.start_time.slice(0, 5)} · {s.subject.code}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={() => save.mutate()}
              disabled={save.isPending || students.length === 0}
              className="rounded-full bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold shadow-soft disabled:opacity-60"
            >
              {save.isPending ? "Saving…" : "Save attendance"}
            </button>
          </div>
        }
      />

      <div className="grid gap-3 sm:grid-cols-4 mb-6">
        {counts.map((c) => (
          <div key={c.key} className="rounded-2xl border border-border bg-card p-4">
            <div className="text-xs text-muted-foreground">{c.label}</div>
            <div className="mt-1 flex items-center justify-between">
              <span className="font-display text-2xl font-bold">{c.count}</span>
              <Badge tone={c.key === "present" ? "success" : c.key === "absent" ? "danger" : c.key === "late" ? "warning" : "info"}>
                {c.short}
              </Badge>
            </div>
          </div>
        ))}
      </div>

      <Card title="Roster">
        {studentsLoading ? <Spinner /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                <tr><th className="py-2">Roll</th><th>Name</th><th>Today</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {students.map((s) => {
                  const current = roster[s.id] ?? "present";
                  return (
                    <tr key={s.id}>
                      <td className="py-3 font-mono text-xs">{s.roll_number}</td>
                      <td className="font-medium">{s.full_name}</td>
                      <td>
                        <div className="flex gap-1">
                          {STATUS_KEYS.map((k) => (
                            <button
                              key={k.key}
                              onClick={() => setRoster((p) => ({ ...p, [s.id]: k.key }))}
                              className={
                                "h-8 w-8 rounded-lg text-xs font-bold transition " +
                                (current === k.key
                                  ? k.key === "present" ? "bg-success text-success-foreground"
                                    : k.key === "absent" ? "bg-destructive text-destructive-foreground"
                                    : k.key === "late" ? "bg-warning text-warning-foreground"
                                    : "bg-info text-info-foreground"
                                  : "bg-muted text-muted-foreground hover:bg-card")
                              }
                            >
                              {k.short}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {students.length === 0 && (
                  <tr><td colSpan={3} className="py-6 text-center text-muted-foreground">No students found for this class.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}