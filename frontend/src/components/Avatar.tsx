import type { UserBrief } from '@/api/types'

export function Avatar({ user, size = 40 }: { user: UserBrief | null; size?: number }) {
  const fallback = (user?.username?.[0] ?? '?').toUpperCase()
  if (!user) {
    return (
      <div
        className="rounded-full bg-ink-100 flex items-center justify-center text-ink-400 font-medium"
        style={{ width: size, height: size }}
      />
    )
  }
  const src = user.avatar_url || undefined
  return (
    <img
      src={src}
      alt={user.username}
      width={size}
      height={size}
      className="rounded-full bg-ink-100 object-cover ring-1 ring-black/5"
      style={{ width: size, height: size }}
      loading="lazy"
      onError={(e) => {
        (e.target as HTMLImageElement).src = `data:image/svg+xml,${encodeURIComponent(
          `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect fill="#e5e5ea" width="${size}" height="${size}"/><text x="50%" y="50%" font-size="${Math.round(size * 0.4)}" text-anchor="middle" dy=".35em" fill="#8e8e93" font-family="-apple-system,system-ui">${fallback}</text></svg>`,
        )}`
      }}
    />
  )
}