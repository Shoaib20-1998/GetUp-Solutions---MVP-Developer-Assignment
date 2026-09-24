import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import { topLevelMessage } from "../../lib/form-errors";
import type { Activity } from "../../lib/types";

const EVENT_LABELS: Record<Activity["event_type"], string> = {
  created: "Created",
  status_changed: "Status changed",
  assigned: "Assigned",
  ai_applied: "AI suggestion applied",
};

export function ActivityLog({ ticketId }: { ticketId: string }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["activity", ticketId],
    queryFn: () => api.get<Activity[]>(`/tickets/${ticketId}/activity`),
  });

  return (
    <section aria-labelledby="activity-heading">
      <h2 id="activity-heading">Activity</h2>
      {isLoading && <p>Loading activity...</p>}
      {isError && <p role="alert">{topLevelMessage(error)}</p>}
      <ul>
        {data?.map((entry) => (
          <li key={entry.id}>
            {EVENT_LABELS[entry.event_type]}
            {entry.from_value && entry.to_value && (
              <> &mdash; {entry.from_value} → {entry.to_value}</>
            )}
            {entry.actor && <> by {entry.actor.full_name}</>}
          </li>
        ))}
      </ul>
    </section>
  );
}
