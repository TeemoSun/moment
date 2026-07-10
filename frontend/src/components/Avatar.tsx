import { UserBrief } from '@/api/types'

export function Avatar({ user, size = 40 }: { user: UserBrief | null; size?: number }) {
  if (!user) return <div className="rounded-full bg-slate-200" style={{ width: size, height: size }} />
  const src = user.avatar_url || undefined
  return (
    <img
      src={src}
      alt={user.username}
      width={size}
      height={size}
      className="rounded-full bg-slate-200 object-cover"
      style={{ width: size, height: size }}
      loading="lazy"
      onError={(e) => { (e.target as HTMLImageElement).src = `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect fill="#e2e8f0" width="${size}" height="${size}"/><text x="50%" y="50%" font-size="16" text-anchor="middle" dy=".3em" fill="#64748b">${user.username[0].toUpperCase()}</text></svg>`)}` }}
    />
  )
}