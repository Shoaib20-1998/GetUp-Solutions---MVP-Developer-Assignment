import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { PriorityBadge } from "../components/Badge";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth-context";
import { topLevelMessage } from "../lib/form-errors";
import type { TicketDetail } from "../lib/types";
import { ActivityLog } from "./ticket-detail/ActivityLog";
import { AiSuggestionPanel } from "./ticket-detail/AiSuggestionPanel";
import { AssigneeControl } from "./ticket-detail/AssigneeControl";
import { CommentThread } from "./ticket-detail/CommentThread";
import { StatusControl } from "./ticket-detail/StatusControl";

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();

  const { data: ticket, isLoading, isError, error } = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api.get<TicketDetail>(`/tickets/${id}`),
    enabled: Boolean(id),
  });

  if (isLoading) return <main>Loading ticket...</main>;
  if (isError) return <main role="alert">{topLevelMessage(error)}</main>;
  if (!ticket) return null;

  const isStaff = user?.role === "agent" || user?.role === "admin";

  return (
    <main>
      <h1>{ticket.title}</h1>
      <p>{ticket.description}</p>
      <p className="meta-line">
        <span className="badge badge-category">{ticket.category}</span>
        <PriorityBadge priority={ticket.priority} />
      </p>
      <p className="muted">Requested by {ticket.requester.full_name}</p>

      {isStaff && <StatusControl ticket={ticket} />}
      {user?.role === "admin" && <AssigneeControl ticket={ticket} />}
      {isStaff && <AiSuggestionPanel ticket={ticket} />}

      {ticket.attachments.length > 0 && (
        <section aria-labelledby="attachments-heading">
          <h2 id="attachments-heading">Attachments</h2>
          <ul>
            {ticket.attachments.map((a) => (
              <li key={a.id}>{a.filename}</li>
            ))}
          </ul>
        </section>
      )}

      <CommentThread ticketId={ticket.id} />

      {isStaff && <ActivityLog ticketId={ticket.id} />}
    </main>
  );
}
