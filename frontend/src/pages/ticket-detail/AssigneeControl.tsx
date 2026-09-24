import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api } from "../../lib/api";
import { topLevelMessage } from "../../lib/form-errors";
import type { Ticket } from "../../lib/types";

export function AssigneeControl({ ticket }: { ticket: Ticket }) {
  const queryClient = useQueryClient();
  const [assigneeId, setAssigneeId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.patch<Ticket>(`/tickets/${ticket.id}/assignee`, { assignee_id: assigneeId }),
    onSuccess: () => {
      setError(null);
      setAssigneeId("");
      queryClient.invalidateQueries({ queryKey: ["ticket", ticket.id] });
      queryClient.invalidateQueries({ queryKey: ["activity", ticket.id] });
    },
    onError: (err) => setError(topLevelMessage(err)),
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div>
      <p>Assignee: {ticket.assignee?.full_name ?? "Unassigned"}</p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="assignee-id">Agent user ID</label>
        <input
          id="assignee-id"
          value={assigneeId}
          onChange={(e) => setAssigneeId(e.target.value)}
          required
          placeholder="Agent's user id"
        />
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Assigning..." : "Assign"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
