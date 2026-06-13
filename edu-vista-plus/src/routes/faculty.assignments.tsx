import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader, Card, Badge, Spinner } from "@/components/AppShell";
import { facultyApi, type AssignmentCreate } from "@/lib/api/endpoints";

export const Route = createFileRoute("/faculty/assignments")({
  head: () => ({ meta: [{ title: "Assignments · Faculty · Campus OS" }] }),
  component: FacultyAssignments,
});

function FacultyAssignments() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [gradeModal, setGradeModal] = useState<{ submissionId: string; studentName: string; max: number } | null>(null);
  const [marks, setMarks] = useState("");
  const [feedback, setFeedback] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<AssignmentCreate>({ title: "", subject_id: "", due_date: "", max_marks: 100 });

  const { data: assignments = [], isLoading } = useQuery({
    queryKey: ["faculty-assignments"],
    queryFn: facultyApi.assignments,
  });

  const { data: courseAssignments = [] } = useQuery({
    queryKey: ["course-assignments"],
    queryFn: facultyApi.courseAssignments,
  });

  const { data: submissions = [], isLoading: subsLoading } = useQuery({
    queryKey: ["submissions", selectedId],
    queryFn: () => facultyApi.getSubmissions(selectedId!),
    enabled: !!selectedId,
  });

  const gradeSubmission = useMutation({
    mutationFn: () => facultyApi.gradeSubmission(gradeModal!.submissionId, Number(marks), feedback || undefined),
    onSuccess: () => {
      toast.success("Graded!");
      qc.invalidateQueries({ queryKey: ["submissions", selectedId] });
      qc.invalidateQueries({ queryKey: ["faculty-assignments"] });
      setGradeModal(null);
      setMarks("");
      setFeedback("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const createAssignment = useMutation({
    mutationFn: () => facultyApi.createAssignment(form),
    onSuccess: () => {
      toast.success("Assignment created!");
      qc.invalidateQueries({ queryKey: ["faculty-assignments"] });
      setShowCreate(false);
      setForm({ title: "", subject_id: "", due_date: "", max_marks: 100 });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) return <Spinner />;

  const selected = assignments.find((a) => a.id === selectedId) ?? null;
  const ungradedCount = submissions.filter((s) => s.marks === null).length;

  return (
    <>
      <PageHeader
        eyebrow="Assignments"
        title="Create, distribute, grade"
        subtitle="Track submissions in real-time and publish grades when ready."
        action={
          <button onClick={() => setShowCreate((v) => !v)} className="rounded-full bg-primary text-primary-foreground px-4 py-2 text-sm font-semibold">
            {showCreate ? "Cancel" : "+ New assignment"}
          </button>
        }
      />

      {showCreate && (
        <Card title="New assignment" className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="text-sm font-semibold">Title</label>
              <input value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" placeholder="e.g. Lab Report 4 — Regression" />
            </div>
            <div>
              <label className="text-sm font-semibold">Subject</label>
              <select value={form.subject_id} onChange={(e) => setForm((p) => ({ ...p, subject_id: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm">
                <option value="">Select subject</option>
                {courseAssignments.map((ca) => (
                  <option key={ca.subject.id} value={ca.subject.id}>{ca.subject.name} ({ca.section})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-semibold">Due date</label>
              <input type="datetime-local" value={form.due_date} onChange={(e) => setForm((p) => ({ ...p, due_date: e.target.value }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="text-sm font-semibold">Max marks</label>
              <input type="number" value={form.max_marks} onChange={(e) => setForm((p) => ({ ...p, max_marks: Number(e.target.value) }))}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-3">
            <button onClick={() => setShowCreate(false)} className="rounded-full border border-border px-4 py-2 text-sm">Cancel</button>
            <button onClick={() => createAssignment.mutate()} disabled={createAssignment.isPending || !form.title || !form.subject_id}
              className="rounded-full bg-primary text-primary-foreground px-5 py-2 text-sm font-semibold disabled:opacity-60">
              {createAssignment.isPending ? "Creating…" : "Create"}
            </button>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Assignments" className="lg:col-span-1">
          <div className="space-y-3">
            {assignments.length === 0 && <p className="text-sm text-muted-foreground">No assignments yet.</p>}
            {assignments.map((a) => (
              <button key={a.id} onClick={() => setSelectedId(a.id)}
                className={`w-full text-left rounded-2xl p-4 transition ${selectedId === a.id ? "bg-primary/10 border border-primary" : "bg-surface hover:border-border border border-transparent"}`}>
                <div className="font-semibold text-sm">{a.title}</div>
                <div className="text-xs text-muted-foreground mt-1">{a.subject.code} · Due {new Date(a.due_date).toLocaleDateString()}</div>
                <div className="mt-2">
                  <Badge tone={a.status === "graded" ? "success" : a.status === "open" ? "warning" : "neutral"}>{a.status}</Badge>
                </div>
              </button>
            ))}
          </div>
        </Card>

        <Card title={selected ? `${selected.title} — Submissions` : "Select an assignment"} className="lg:col-span-2"
          action={ungradedCount > 0 ? <Badge tone="warning">{ungradedCount} ungraded</Badge> : undefined}>
          {!selected ? (
            <p className="text-sm text-muted-foreground">Click an assignment on the left to see submissions.</p>
          ) : subsLoading ? (
            <Spinner />
          ) : submissions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No submissions yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <tr><th className="py-2">Student</th><th>Submitted</th><th>Grade</th><th></th></tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {submissions.map((s) => (
                    <tr key={s.id}>
                      <td className="py-3 font-medium">{s.student_name ?? "—"}</td>
                      <td className="text-xs text-muted-foreground">{new Date(s.submitted_at).toLocaleDateString()}</td>
                      <td>
                        {s.marks !== null
                          ? <Badge tone="success">{s.marks}/{selected.max_marks}</Badge>
                          : <Badge tone="warning">Pending</Badge>}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          {s.file_url && (
                            <a href={s.file_url} target="_blank" rel="noopener noreferrer"
                              className="text-xs font-semibold text-primary">View</a>
                          )}
                          {s.marks === null && (
                            <button onClick={() => setGradeModal({ submissionId: s.id, studentName: s.student_name ?? "", max: selected.max_marks })}
                              className="rounded-full bg-primary text-primary-foreground px-3 py-1 text-xs font-semibold">
                              Grade
                            </button>
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
      </div>

      {gradeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur p-4">
          <div className="w-full max-w-sm rounded-3xl bg-card border border-border p-6 shadow-xl">
            <div className="font-semibold text-lg mb-4">Grade: {gradeModal.studentName}</div>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-semibold">Marks (out of {gradeModal.max})</label>
                <input type="number" min={0} max={gradeModal.max} value={marks} onChange={(e) => setMarks(e.target.value)}
                  className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-sm font-semibold">Feedback (optional)</label>
                <textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} rows={3}
                  className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm resize-none" />
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <button onClick={() => setGradeModal(null)} className="flex-1 rounded-full border border-border py-2 text-sm">Cancel</button>
              <button onClick={() => gradeSubmission.mutate()} disabled={gradeSubmission.isPending || !marks}
                className="flex-1 rounded-full bg-primary text-primary-foreground py-2 text-sm font-semibold disabled:opacity-60">
                {gradeSubmission.isPending ? "Saving…" : "Save grade"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}