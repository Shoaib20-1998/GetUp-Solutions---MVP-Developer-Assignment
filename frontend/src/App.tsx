import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AuthProvider } from "./lib/auth-context";
import { RequireAuth, RequireRole } from "./lib/route-guards";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { NewTicketPage } from "./pages/NewTicketPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";
import { TicketListPage } from "./pages/TicketListPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route element={<RequireAuth />}>
              <Route element={<AppLayout />}>
                <Route path="/tickets" element={<TicketListPage />} />
                <Route path="/tickets/new" element={<NewTicketPage />} />
                <Route path="/tickets/:id" element={<TicketDetailPage />} />

                <Route element={<RequireRole roles={["admin"]} />}>
                  <Route path="/dashboard" element={<DashboardPage />} />
                </Route>
              </Route>
            </Route>

            <Route path="/" element={<Navigate to="/tickets" replace />} />
            <Route path="*" element={<Navigate to="/tickets" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
