import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { PageHeader, Spinner } from "@/components/AppShell";
import { studentApi, type ChatSession } from "@/lib/api/endpoints";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/student/chat")({
  head: () => ({ meta: [{ title: "AI Assistant · Student · Campus OS" }] }),
  component: ChatPage,
});

function ChatPage() {
  const qc = useQueryClient();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: studentApi.chatSessions,
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["chat-history", sessionId],
    queryFn: () => studentApi.chatHistory(sessionId!),
    enabled: !!sessionId,
  });

  useEffect(() => {
    if (history) {
      setMessages(history.messages.map((m) => ({ role: m.role, content: m.content })));
    }
  }, [history]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useMutation({
    mutationFn: () => studentApi.chat(input.trim(), sessionId ?? undefined),
    onMutate: () => {
      const userMsg = input.trim();
      setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
      setInput("");
    },
    onSuccess: (data) => {
      if (!sessionId) setSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
    },
    onError: (e: Error) => {
      setMessages((prev) => prev.slice(0, -1));
      toast.error(e.message);
    },
  });

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !send.isPending) send.mutate();
    }
  }

  function newSession() {
    setSessionId(null);
    setMessages([]);
  }

  function loadSession(s: ChatSession) {
    setSessionId(s.id);
    setMessages([]);
  }

  return (
    <div className="h-[calc(100vh-10rem)] flex gap-6">
      <aside className="hidden lg:flex w-64 shrink-0 flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-muted-foreground">Sessions</span>
          <button onClick={newSession} className="text-xs font-semibold text-primary">+ New</button>
        </div>
        {sessionsLoading ? (
          <Spinner />
        ) : sessions.length === 0 ? (
          <p className="text-xs text-muted-foreground">No sessions yet. Start chatting!</p>
        ) : (
          <div className="space-y-1 overflow-y-auto flex-1">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => loadSession(s)}
                className={cn(
                  "w-full rounded-xl p-3 text-left text-sm transition-colors",
                  sessionId === s.id ? "bg-primary text-primary-foreground" : "hover:bg-card border border-border",
                )}
              >
                <div className="font-medium line-clamp-1">{s.title}</div>
                <div className={cn("text-xs mt-0.5", sessionId === s.id ? "text-primary-foreground/70" : "text-muted-foreground")}>
                  {s.message_count} messages
                </div>
              </button>
            ))}
          </div>
        )}
      </aside>

      <div className="flex flex-1 flex-col rounded-3xl border border-border bg-card overflow-hidden">
        <div className="border-b border-border p-4">
          <PageHeader
            eyebrow="AI Assistant"
            title="Campus AI"
            subtitle="Ask about attendance, assignments, fees, or anything academic."
          />
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !historyLoading && (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="text-4xl mb-4">🤖</div>
              <div className="font-semibold text-lg">Ask me anything</div>
              <p className="text-sm text-muted-foreground mt-2 max-w-sm">
                I have access to your attendance, assignments, fees, and certificates. Try asking about your attendance risk or upcoming deadlines.
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  "What's my attendance risk?",
                  "Which assignments are pending?",
                  "How much fees do I owe?",
                  "Predict my performance",
                ].map((q) => (
                  <button key={q} onClick={() => { setInput(q); }}
                    className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium hover:bg-muted transition">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {historyLoading && <Spinner />}

          {messages.map((m, i) => (
            <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              {m.role === "assistant" && (
                <div className="mr-3 mt-1 h-8 w-8 shrink-0 rounded-full bg-gradient-cool grid place-items-center text-sm">🤖</div>
              )}
              <div className={cn(
                "max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap",
                m.role === "user"
                  ? "bg-primary text-primary-foreground rounded-br-sm"
                  : "bg-surface border border-border rounded-bl-sm",
              )}>
                {m.content}
              </div>
            </div>
          ))}

          {send.isPending && (
            <div className="flex justify-start">
              <div className="mr-3 mt-1 h-8 w-8 shrink-0 rounded-full bg-gradient-cool grid place-items-center text-sm">🤖</div>
              <div className="bg-surface border border-border rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex gap-1">
                  <div className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="border-t border-border p-4">
          <div className="flex gap-3 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about your academics… (Enter to send, Shift+Enter for newline)"
              rows={1}
              className="flex-1 resize-none rounded-2xl border border-border bg-surface px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[42px] max-h-32"
            />
            <button
              onClick={() => { if (input.trim() && !send.isPending) send.mutate(); }}
              disabled={!input.trim() || send.isPending}
              className="rounded-full bg-primary text-primary-foreground px-5 py-2.5 text-sm font-semibold disabled:opacity-50 shrink-0"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
