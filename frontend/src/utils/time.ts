export function parseUTC(dateStr: string): Date {
  // 后端（Go）返回 RFC3339，自带 Z 或 ±HH:MM 时区后缀；仅对无时区的裸 UTC 字符串补 Z
  return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(dateStr) ? new Date(dateStr) : new Date(`${dateStr}Z`);
}

export function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = parseUTC(dateStr).getTime();
  const diff = Math.max(0, now - then);
  const seconds = Math.floor(diff / 1000);

  if (seconds < 60) return "刚刚";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}个月前`;
  const years = Math.floor(months / 12);
  return `${years}年前`;
}
