import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../lib/api";
import { topLevelMessage } from "../../lib/form-errors";
import type { Comment, TicketDetail } from "../../lib/types";

// Nothing in this panel writes to the ticket without an explicit click.
// `ai_summary`/`ai_draft_reply` are read-only display of what the mock
// provider produced; Apply is the only action that promotes a suggestion
// into a real field (Requirement 9.3), and posting the draft reply goes
// through the normal comment endpoint, never bypassing it.
export function AiSuggestionPanel({ ticket }: { ticket: TicketDetail }) {
  const queryClient = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [draftReply, setDraftReply] = useState(ticket.ai_draft_reply ?? "");
  const [error, setError] = useState<string | null>(null);

  const applyMutation = useMutation({
    mutationFn: (field: "category" | "priority") =>
      api.post<TicketDetail>(`/tickets/${ticket.id}/ai/apply`, { field }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["ticket", ticket.id] });
      queryClient.invalidateQueries({ queryKey: ["activity", ticket.id] });
    },
    onError: (err) => setError(topLevelMessage(err)),
  });

  const postReplyMutation = useMutation({
    mutationFn: () =>
      api.post<Comment>(`/tickets/${ticket.id}/comments`, {
        body: draftReply,
        is_internal: false,
      }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["comments", ticket.id] });
    },
    onError: (err) => setError(topLevelMessage(err)),
  });

  const hasAnySuggestion =
    ticket.ai_suggested_category || ticket.ai_suggested_priority || ticket.ai_summary;

  if (dismissed) return null;

  return (
    <section aria-labelledby="ai-heading">
      <h2 id="ai-heading">
        <span aria-hidden="true">✦</span> AI suggested
      </h2>

      {!hasAnySuggestion && <p>No AI suggestions are available for this ticket.</p>}

      {hasAnySuggestion && (
        <>
          {ticket.ai_summary && <p>Summary: {ticket.ai_summary}</p>}

          {ticket.ai_suggested_category && (
            <p>
              Suggested category: {ticket.ai_suggested_category}{" "}
              <button
                type="button"
                disabled={applyMutation.isPending}
                onClick={() => applyMutation.mutate("category")}
              >
                Apply suggested category
              </button>
            </p>
          )}

          {ticket.ai_suggested_priority && (
            <p>
              Suggested priority: {ticket.ai_suggested_priority}{" "}
              <button
                type="button"
                disabled={applyMutation.isPending}
                onClick={() => applyMutation.mutate("priority")}
              >
                Apply suggested priority
              </button>
            </p>
          )}

          <button type="button" onClick={() => setDismissed(true)}>
            Dismiss
          </button>
        </>
      )}

      {ticket.ai_draft_reply && (
        <div>
          <label htmlFor="draft-reply">Draft reply (AI-generated, edit before sending)</label>
          <textarea
            id="draft-reply"
            value={draftReply}
            onChange={(e) => setDraftReply(e.target.value)}
          />
          <button
            type="button"
            disabled={postReplyMutation.isPending || !draftReply.trim()}
            onClick={() => postReplyMutation.mutate()}
          >
            {postReplyMutation.isPending ? "Posting..." : "Send as comment"}
          </button>
        </div>
      )}

      {error && <p role="alert">{error}</p>}
    </section>
  );
}
