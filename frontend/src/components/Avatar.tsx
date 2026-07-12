import type { UserBrief } from '@/api/types'

const AVATAR_COLORS: [string, string][] = [
  ['#e5e5ea', '#8e8e93'],
  ['#dbeafe', '#3b82f6'],
  ['#ede9fe', '#7c3aed'],
  ['#fce7f3', '#db2777'],
  ['#d1fae5', '#059669'],
  ['#fef3c7', '#d97706'],
]

function colorForName(name: string): [string, string] {
  const idx = [...name].reduce((sum, c) => sum + c.charCodeAt(0), 0) % AVATAR_COLORS.length
  return AVATAR_COLORS[idx]
}

function initialsSvg(name: string, size: number): string {
  const letter = (name?.[0] ?? '?').toUpperCase()
  const [bg, fg] = colorForName(name)
  return `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect fill="${bg}" width="${size}" height="${size}" rx="${size / 2}"/><text x="50%" y="50%" font-size="${Math.round(size * 0.4)}" text-anchor="middle" dy=".35em" fill="${fg}" font-family="-apple-system,system-ui">${letter}</text></svg>`,
  )}`
}

export function Avatar({ user, size = 40 }: { user: UserBrief | null; size?: number }) {
  if (!user) {
    return (
      <img
        src={initialsSvg('?', size)}
        alt=""
        width={size}
        height={size}
        className="rounded-full ring-1 ring-black/5"
        style={{ width: size, height: size }}
      />
    )
  }
  const name = user.display_name || user.username
  const src = user.avatar_url || initialsSvg(name, size)
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
        (e.target as HTMLImageElement).src = initialsSvg(name, size)
      }}
    />
  )
}