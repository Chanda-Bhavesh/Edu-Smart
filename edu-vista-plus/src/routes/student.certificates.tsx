import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader, Card, Badge, Spinner } from "@/components/AppShell";
import { studentApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/student/certificates")({
  head: () => ({ meta: [{ title: "Certificates · Student · Campus OS" }] }),
  component: CertsPage,
});

const CERT_TYPES = [
  "Bonafide Certificate",
  "Character Certificate",
  "Transfer Certificate",
  "Course Completion Certificate",
  "No Dues Certificate",
  "Internship Permission Letter",
];

function CertsPage() {
  const qc = useQueryClient();
  const [certType, setCertType] = useState(CERT_TYPES[0]);
  const [purpose, setPurpose] = useState("");
  const [showForm, setShowForm] = useState(false);

  const { data: certs = [], isLoading } = useQuery({
    queryKey: ["student-certs"],
    queryFn: studentApi.certificates,
  });

  const apply = useMutation({
    mutationFn: () => studentApi.requestCertificate(certType, purpose || undefined),
    onSuccess: () => {
      toast.success("Certificate request submitted!");
      qc.invalidateQueries({ queryKey: ["student-certs"] });
      setShowForm(false);
      setPurpose("");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) return <Spinner />;

  const pending = certs.filter((c) => c.status === "pending" || c.status === "under_review");
  const approved = certs.filter((c) => c.status === "approved" || c.status === "issued");
  const rejected = certs.filter((c) => c.status === "rejected");

  const statusTone = (s: string) =>
    s === "approved" || s === "issued" ? "success" : s === "rejected" ? "danger" : "warning";

  return (
    <>
      <PageHeader
        eyebrow="Certificates"
        title="Certificate requests"
        subtitle="Request official certificates from the admin office."
        action={
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-full bg-primary text-primary-foreground px-5 py-2.5 text-sm font-semibold shadow-soft"
          >
            {showForm ? "Cancel" : "New request"}
          </button>
        }
      />

      {showForm && (
        <Card title="Request a certificate" className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-semibold">Certificate type</label>
              <select
                value={certType}
                onChange={(e) => setCertType(e.target.value)}
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {CERT_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-semibold">Purpose / reason</label>
              <input
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Bank account opening, visa application…"
                className="mt-1 w-full rounded-2xl border border-border bg-surface px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={() => apply.mutate()}
              disabled={apply.isPending}
              className="rounded-full bg-primary text-primary-foreground px-5 py-2 text-sm font-semibold disabled:opacity-60"
            >
              {apply.isPending ? "Submitting…" : "Submit request"}
            </button>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {[
          { label: "Pending / Under review", items: pending, tone: "warning" as const },
          { label: "Approved / Issued", items: approved, tone: "success" as const },
          { label: "Rejected", items: rejected, tone: "danger" as const },
        ].map((g) => (
          <Card key={g.label} title={g.label} action={<Badge tone={g.tone}>{g.items.length}</Badge>}>
            <div className="space-y-3">
              {g.items.length === 0 && (
                <p className="text-sm text-muted-foreground">Nothing here.</p>
              )}
              {g.items.map((c) => (
                <div key={c.id} className="rounded-2xl border border-border/60 bg-surface p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-semibold text-sm">{c.certificate_type}</div>
                    <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Requested {new Date(c.created_at).toLocaleDateString()}
                  </div>
                  {c.purpose && (
                    <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{c.purpose}</p>
                  )}
                  {c.certificate_number && (
                    <p className="text-xs mt-2 font-mono text-muted-foreground">#{c.certificate_number}</p>
                  )}
                  {(c.status === "approved" || c.status === "issued") && (
                    <a
                      href={studentApi.downloadCertificate(c.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-3 inline-block text-xs font-semibold text-primary"
                    >
                      Download certificate →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}