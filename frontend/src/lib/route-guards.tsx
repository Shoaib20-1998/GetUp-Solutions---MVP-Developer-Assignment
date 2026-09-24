import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./auth-context";
import type { Role } from "./types";

export function RequireAuth() {
  const { token, isLoading } = useAuth();
  if (isLoading) return <p>Loading...</p>;
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

// A convenience guard only: hides routes the caller's role should not use.
// The API enforces the real restriction (Requirement 2.2); this just keeps
// someone from landing on a dead-end screen.
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/tickets" replace />;
  }
  return <Outlet />;
}
