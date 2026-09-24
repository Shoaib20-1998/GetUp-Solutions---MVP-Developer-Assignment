export type Role = "customer" | "agent" | "admin";
export type Status = "open" | "in_progress" | "resolved" | "closed";
export type Priority = "low" | "medium" | "high" | "urgent";
export type Category = "billing" | "technical" | "account" | "general";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
}

export interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  category: Category;
  priority: Priority;
  status: Status;
  requester: User;
  assignee: User | null;
  ai_suggested_category: Category | null;
  ai_suggested_priority: Priority | null;
  ai_summary: string | null;
  ai_draft_reply: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface TicketDetail extends Ticket {
  attachments: Attachment[];
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
}

export interface Comment {
  id: string;
  ticket_id: string;
  author: User;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface Activity {
  id: string;
  ticket_id: string;
  actor: User | null;
  event_type: "created" | "status_changed" | "assigned" | "ai_applied";
  from_value: string | null;
  to_value: string | null;
  created_at: string;
}

export interface Dashboard {
  counts_by_status: Record<Status, number>;
  counts_by_priority: Record<Priority, number>;
  average_resolution_hours: number | null;
  stale_open_count: number;
}
