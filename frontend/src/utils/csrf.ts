export function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)moments_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}
