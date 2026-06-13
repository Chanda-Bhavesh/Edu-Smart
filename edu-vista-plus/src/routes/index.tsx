import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { ROLES } from "@/lib/mock-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Campus OS — Smart Campus Management" },
      { name: "description", content: "Pick a role to explore the Campus OS demo — student, faculty, dept admin or org admin." },
      { property: "og:title", content: "Campus OS — Smart Campus Management" },
      { property: "og:description", content: "A friendly, all-in-one campus platform." },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="relative overflow-hidden">
        <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-gradient-warm opacity-30 blur-3xl" />
        <div className="absolute top-40 -left-32 h-96 w-96 rounded-full bg-gradient-cool opacity-30 blur-3xl" />

        <header className="relative z-10 flex items-center justify-between px-6 lg:px-12 py-6">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-warm text-primary-foreground text-lg shadow-soft">
              ✦
            </span>
            <div className="font-display text-xl font-bold">Campus OS</div>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#roles" className="hover:text-foreground">Roles</a>
            <a href="#features" className="rounded-full bg-foreground text-background px-4 py-2 font-semibold">Watch demo</a>
          </div>
        </header>

        <section className="relative z-10 px-6 lg:px-12 pt-10 pb-16 lg:pt-16 lg:pb-24 max-w-6xl mx-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-semibold text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-success" /> Smart Campus Management System · v1
          </div>
          <h1 className="mt-6 text-5xl lg:text-7xl font-bold tracking-tight leading-[1.05]">
            One warm home for your <span className="bg-gradient-warm bg-clip-text text-transparent">whole campus</span>.
          </h1>
          <p className="mt-6 text-lg text-muted-foreground max-w-2xl">
            Attendance, assignments, fees, certificates, announcements and analytics — built for students,
            faculty and administrators who'd rather spend time learning than chasing forms.
          </p>

          <div id="roles" className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {ROLES.map((r) => (
              <Link
                key={r.id}
                to={
                  r.id === "student" ? "/student"
                  : r.id === "faculty" ? "/faculty"
                  : r.id === "dept-admin" ? "/dept-admin"
                  : r.id === "warden" ? "/warden"
                  : "/org-admin"
                }
                className="group rounded-3xl border border-border bg-card p-6 text-left shadow-soft transition-all hover:-translate-y-1 hover:shadow-pop"
              >
                <div className={`grid h-14 w-14 place-items-center rounded-2xl ${r.accent} text-2xl shadow-soft`}>
                  {r.emoji}
                </div>
                <div className="mt-5 font-display text-xl font-bold">{r.title}</div>
                <p className="mt-1 text-sm text-muted-foreground">{r.tagline}</p>
                <div className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-primary">
                  Enter workspace
                  <span className="transition-transform group-hover:translate-x-1">→</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section id="features" className="relative z-10 px-6 lg:px-12 pb-24 max-w-6xl mx-auto">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              { icon: "📅", title: "Attendance, three ways", body: "Manual, QR or face recognition. AI flags students drifting below 75%." },
              { icon: "💳", title: "Fees & receipts", body: "UPI, cards, net banking. Auto-receipts and clear pending balances." },
              { icon: "📜", title: "Certificates on rails", body: "Bonafide, internship, NOC — student applies, faculty + admin approve, done." },
              { icon: "📝", title: "Assignments end-to-end", body: "Create, submit, grade and publish — no email threads required." },
              { icon: "🔔", title: "Announcements that land", body: "College, department or subject — push to dashboards and inboxes." },
              { icon: "🤖", title: "AI you can trust", body: "Attendance risk, GPA forecasts and a campus chatbot that actually helps." },
            ].map((f) => (
              <div key={f.title} className="rounded-3xl border border-border bg-card p-6 shadow-soft">
                <div className="text-2xl">{f.icon}</div>
                <div className="mt-3 font-display text-lg font-semibold">{f.title}</div>
                <p className="mt-1 text-sm text-muted-foreground">{f.body}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer className="border-t border-border px-6 lg:px-12 py-8 text-sm text-muted-foreground flex flex-wrap items-center justify-between gap-3">
        <div>© 2026 Campus OS · A demo Smart Campus Management System</div>
        <div className="flex gap-4">
          <a href="#" className="hover:text-foreground">Privacy</a>
          <a href="#" className="hover:text-foreground">Terms</a>
          <a href="#" className="hover:text-foreground">Contact</a>
        </div>
      </footer>
    </div>
  );
}
