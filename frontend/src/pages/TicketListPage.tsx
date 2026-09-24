import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { PriorityBadge, StatusBadge } from "../components/Badge";
import { api } from "../lib/api";
import { topLevelMessage } from "../lib/form-errors";
import type { Priority, Status, TicketListResponse } from "../lib/types";

const STATUS_OPTIONS: Status[] = ["open", "in_progress", "resolved", "closed"];
const PRIORITY_OPTIONS: Priority[] = ["low", "medium", "high", "urgent"];

export function TicketListPage() {
  const [status, setStatus] = useState<Status | "">("");
  const [priority, setPriority] = useState<Priority | "">("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);
  if (q) params.set("q", q);
  params.set("page", String(page));

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["tickets", status, priority, q, page],
    queryFn: () => api.get<TicketListResponse>(`/tickets?${params.toString()}`),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <main>
      <h1>Tickets</h1>

      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          setPage(1);
        }}
      >
        <label htmlFor="status-filter">Status</label>
        <select
          id="status-filter"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as Status | "");
            setPage(1);
          }}
        >
          <option value="">All</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <label htmlFor="priority-filter">Priority</label>
        <select
          id="priority-filter"
          value={priority}
          onChange={(e) => {
            setPriority(e.target.value as Priority | "");
            setPage(1);
          }}
        >
          <option value="">All</option>
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>

        <label htmlFor="q">Search</label>
        <input
          id="q"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search title or description"
        />
        <button type="submit">Search</button>
      </form>

      {isLoading && <p>Loading tickets...</p>}
      {isError && <p role="alert">{topLevelMessage(error)}</p>}

      {data && (
        <>
          <table>
            <thead>
              <tr>
                <th scope="col">Title</th>
                <th scope="col">Status</th>
                <th scope="col">Priority</th>
                <th scope="col">Requester</th>
                <th scope="col">Assignee</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((ticket) => (
                <tr key={ticket.id}>
                  <td>
                    <Link to={`/tickets/${ticket.id}`}>{ticket.title}</Link>
                  </td>
                  <td><StatusBadge status={ticket.status} /></td>
                  <td><PriorityBadge priority={ticket.priority} /></td>
                  <td>{ticket.requester.full_name}</td>
                  <td>{ticket.assignee?.full_name ?? "Unassigned"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {data.items.length === 0 && <p>No tickets match these filters.</p>}

          <nav aria-label="Pagination">
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </main>
  );
}
