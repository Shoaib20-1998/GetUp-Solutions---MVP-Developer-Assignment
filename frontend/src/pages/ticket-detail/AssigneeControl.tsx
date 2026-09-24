import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api } from "../../lib/api";
import { topLevelMessage } from "../../lib/form-errors";
import type { Ticket } from "../../lib/types";

interface UserSummary {
  id: string;
  full_name: string;
  email: string;
}

export function AssigneeControl({ ticket }: { ticket: Ticket }) {
  const queryClient = useQueryClient();
  const [assigneeId, setAssigneeId] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Admin-only endpoint that powers this picker; see backend/app/routers/users.py.
  const { data: agents, isLoading: isLoadingAgents } = useQuery({
    queryKey: ["users", "agent"],
    queryFn: () => api.get<UserSummary[]>("/users?role=agent"),
  });

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
    if (!assigneeId) return;
    mutation.mutate();
  }

  return (
    <div>
      <p>Assignee: {ticket.assignee?.full_name ?? "Unassigned"}</p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="assignee-id">Assign to agent</label>
        <select
          id="assignee-id"
          value={assigneeId}
          onChange={(e) => setAssigneeId(e.target.value)}
          required
        >
          <option value="">
            {isLoadingAgents ? "Loading agents..." : "Select an agent"}
          </option>
          {agents?.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.full_name} ({agent.email})
            </option>
          ))}
        </select>
        <button type="submit" disabled={mutation.isPending || !assigneeId}>
          {mutation.isPending ? "Assigning..." : "Assign"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
