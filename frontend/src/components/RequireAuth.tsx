import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
