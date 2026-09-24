import type { Priority, Status } from "../lib/types";

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge-status-${status}`}>{status.replace("_", " ")}</span>;
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <span className={`badge badge-priority-${priority}`}>{priority}</span>;
}
