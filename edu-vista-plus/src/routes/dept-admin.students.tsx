import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader, Card, Badge, Spinner } from "@/components/AppShell";
import { adminApi } from "@/lib/api/endpoints";

export const Route = createFileRoute("/dept-admin/students")({
  head: () => ({ meta: [{ title: "Students · Dept admin · Campus OS" }] }),
  component: DeptStudents,
});

function DeptStudents() {
  const [search, setSearch] = useState("");

  const { data: students = [], isLoading } = useQuery({
    queryKey: ["admin-students"],
    queryFn: () => adminApi.students(),
  });

  const { data: atRisk = [] } = useQuery({
    queryKey: ["at-risk"],
    queryFn: adminApi.atRiskStudents,
  });

  if (isLoading) return <Spinner />;

  const riskMap = Object.fromEntries(atRisk.map((r) => [r.student_id, r]));

  const filtered = students.filter((s) => {
    const q = search.toLowerCase();
    return !q || s.user.full_name.toLowerCase().includes(q) || s.roll_number.toLowerCase().includes(q);
  });

  return (
    <>
      <PageHeader
        eyebrow="Students"
        title="Manage your department's roster"
        subtitle="Search, filter, edit and track every student."
      />

      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 min-w-[200px] rounded-full bg-muted px-4 py-2 text-sm outline-none placeholder:text-muted-foreground"
            placeholder="Search by name or roll number…"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wider text-muted-foreground">
              <tr><th className="py-2">Roll</th><th>Name</th><th>Dept</th><th>Sem</th><th>Risk</th></tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.length === 0 && (
                <tr><td colSpan={5} className="py-6 text-center text-muted-foreground">No students found.</td></tr>
              )}
              {filtered.map((s) => {
                const risk = riskMap[s.id];
                return (
                  <tr key={s.id}>
                    <td className="py-3 font-mono text-xs">{s.roll_number}</td>
                    <td className="font-medium">{s.user.full_name}</td>
                    <td className="text-muted-foreground text-xs">{s.department.name}</td>
                    <td className="text-muted-foreground text-xs">Sem {s.semester.number}</td>
                    <td>
                      {risk ? (
                        <Badge tone={risk.overall_risk_level === "critical" ? "danger" : risk.overall_risk_level === "high" ? "warning" : "success"}>
                          {risk.overall_risk_level}
                        </Badge>
                      ) : (
                        <Badge tone="success">Low</Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}