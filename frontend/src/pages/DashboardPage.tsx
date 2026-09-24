import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { topLevelMessage } from "../lib/form-errors";
import type { Dashboard } from "../lib/types";

export function DashboardPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<Dashboard>("/dashboard"),
  });

  if (isLoading) return <main>Loading dashboard...</main>;
  if (isError) return <main role="alert">{topLevelMessage(error)}</main>;
  if (!data) return null;

  return (
    <main>
      <h1>Dashboard</h1>

      <section aria-labelledby="by-status-heading">
        <h2 id="by-status-heading">Tickets by status</h2>
        <ul>
          {Object.entries(data.counts_by_status).map(([status, count]) => (
            <li key={status}>
              {status}: {count}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="by-priority-heading">
        <h2 id="by-priority-heading">Tickets by priority</h2>
        <ul>
          {Object.entries(data.counts_by_priority).map(([priority, count]) => (
            <li key={priority}>
              {priority}: {count}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="resolution-heading">
        <h2 id="resolution-heading">Average time to resolution</h2>
        <p>
          {data.average_resolution_hours === null
            ? "Unavailable (no tickets resolved yet)"
            : `${data.average_resolution_hours.toFixed(1)} hours`}
        </p>
      </section>

      <section aria-labelledby="stale-heading">
        <h2 id="stale-heading">Open longer than 48 hours</h2>
        <p>{data.stale_open_count}</p>
      </section>
    </main>
  );
}
