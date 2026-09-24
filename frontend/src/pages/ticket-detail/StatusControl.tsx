import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { StatusBadge } from "../../components/Badge";
import { api } from "../../lib/api";
import { topLevelMessage } from "../../lib/form-errors";
import type { Status, Ticket } from "../../lib/types";

// Mirrors the backend's allowed-transition map so the UI only ever offers a
// move the API will actually accept. The API is still the real check
// (Requirement 2.2); this just avoids offering a doomed click.
const NEXT_STATUS: Record<Status, Status | null> = {
  open: "in_progress",
  in_progress: "resolved",
  resolved: "closed",
  closed: null,
};

const LABELS: Record<Status, string> = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

export function StatusControl({ ticket }: { ticket: Ticket }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (status: Status) => api.patch<Ticket>(`/tickets/${ticket.id}/status`, { status }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["ticket", ticket.id] });
      queryClient.invalidateQueries({ queryKey: ["activity", ticket.id] });
    },
    onError: (err) => setError(topLevelMessage(err)),
  });

  const next = NEXT_STATUS[ticket.status];

  return (
    <div className="control-row">
      <StatusBadge status={ticket.status} />
      {next && (
        <button
          type="button"
          className="btn btn-secondary"
          disabled={mutation.isPending}
          onClick={() => mutation.mutate(next)}
        >
          Move to {LABELS[next]}
        </button>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
