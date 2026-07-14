import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

interface RequireAuthProps {
  children: ReactNode;
  role?: string;
}

export default function RequireAuth({ children, role }: RequireAuthProps) {
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (role && user.role !== role) {
    return <Navigate to="/feed" replace />;
  }

  return <>{children}</>;
}
