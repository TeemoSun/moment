import { notificationOpen } from "animal-island-ui";

export const notify = {
  success: (message: string, description?: string) =>
    notificationOpen({ message, description, type: "success", position: "top", duration: 3 }),
  error: (message: string, description?: string) =>
    notificationOpen({ message, description, type: "error", position: "top", duration: 5 }),
  info: (message: string, description?: string) =>
    notificationOpen({ message, description, type: "info", position: "top", duration: 3 }),
  warning: (message: string, description?: string) =>
    notificationOpen({ message, description, type: "warning", position: "top", duration: 4 }),
};