import { Link, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../lib/auth-context";

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <header>
        <nav aria-label="Main navigation">
          <Link to="/tickets">Tickets</Link>
          {user?.role === "customer" && <Link to="/tickets/new">New ticket</Link>}
          {user?.role === "admin" && <Link to="/dashboard">Dashboard</Link>}
        </nav>
        {user && (
          <div>
            <span>{user.full_name}</span>
            <button type="button" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <Outlet />
    </div>
  );
}
