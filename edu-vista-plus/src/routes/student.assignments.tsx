import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { toast } from "sonner";
import { PageHeader, Card, Badge, Spinner } from "@/components/AppShell";
import { studentApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/student/assignments")({
  head: () => ({ meta: [{ title: "Assignments · Student · Campus OS" }] }),
  component: AssignmentsPage,
});

function AssignmentsPage() {
  const qc = useQueryClient();
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const { data: assignments = [], isLoading } = useQuery({
    queryKey: ["student-assignments"],
    queryFn: studentApi.assignments,
  });

  const submit = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) => {
      const fd = new FormData();
      fd.append("file", file);
      return studentApi.submitAssignment(id, fd);
    },
    onSuccess: () => {
      toast.success("Assignment submitted!");
      qc.invalidateQueries({ queryKey: ["student-assignments"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) return <Spinner />;

  const pending  = assignments.filter((a) => !a.my_submission && a.status === "open");
  const submitted = assignments.filter((a) => a.my_submission && a.my_submission.marks === null);
  const graded   = assignments.filter((a) => a.my_submission && a.my_submission.marks !== null);

  const groups = [
    { label: "Pending",   items: pending,   tone: "warning" as const },
    { label: "Submitted", items: submitted,  tone: "info"    as const },
    { label: "Graded",    items: graded,     tone: "success" as const },
  ];

  return (
    <>
      <PageHeader eyebrow="Assignments" title="Your assignment board" subtitle="Upload, track, and see grades when published." />
      <div className="grid gap-6 lg:grid-cols-3">
        {groups.map((g) => (
          <Card key={g.label} title={g.label} action={<Badge tone={g.tone}>{g.items.length}</Badge>}>
            <div className="space-y-3">
              {g.items.map((a) => {
                const maxMarks = a.max_marks;
                const marks = a.my_submission?.marks;
                const pct = marks != null ? Math.round((marks / maxMarks) * 100) : null;
                return (
                  <div key={a.id} className="rounded-2xl border border-border/60 bg-surface p-4">
                    <div className="font-semibold">{a.title}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {a.subject.name} · Due {new Date(a.due_date).toLocaleDateString()}
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      {pct != null ? (
                        <span className="font-display text-lg font-bold text-success-foreground">
                          {marks}/{maxMarks} ({pct}%)
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          {a.my_submission ? "Awaiting evaluation" : "Not submitted yet"}
                        </span>
                      )}
                      {!a.my_submission && a.status === "open" && (
                        <>
                          <input
                            type="file"
                            className="hidden"
                            ref={(el) => { fileRefs.current[a.id] = el; }}
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) submit.mutate({ id: a.id, file });
                            }}
                          />
                          <button
                            onClick={() => fileRefs.current[a.id]?.click()}
                            disabled={submit.isPending}
                            className="rounded-full bg-primary text-primary-foreground px-3 py-1.5 text-xs font-semibold disabled:opacity-60"
                          >
                            {submit.isPending ? "Uploading…" : "Upload"}
                          </button>
                        </>
                      )}
                    </div>
                    {a.my_submission?.feedback && (
                      <p className="mt-2 text-xs text-muted-foreground border-t border-border pt-2">
                        Feedback: {a.my_submission.feedback}
                      </p>
                    )}
                  </div>
                );
              })}
              {g.items.length === 0 && <div className="text-sm text-muted-foreground">Nothing here yet.</div>}
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}
