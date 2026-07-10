import { useState } from 'react'
import { X, Play } from 'lucide-react'
import type { Media } from '@/api/types'

export function MediaGrid({ media }: { media: Media[] }) {
  const [lightbox, setLightbox] = useState<string | null>(null)
  if (!media.length) return null

  return (
    <>
      <div className={`grid gap-2 mt-3 ${media.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
        {media.map((m) => (
          <div key={m.id} className="relative rounded-2xl overflow-hidden bg-ink-100 ring-1 ring-black/5">
            {m.media_type === 'image' ? (
              <img
                src={m.small_url || m.original_url || ''}
                alt={m.original_filename}
                className="w-full h-auto object-cover cursor-pointer transition-transform duration-300 ease-apple hover:scale-[1.02]"
                loading="lazy"
                onClick={() => setLightbox(m.original_url || m.medium_url || m.small_url || '')}
              />
            ) : (
              <div className="relative cursor-pointer" onClick={() => setLightbox(m.original_url || '')}>
                <img
                  src={m.small_url || ''}
                  alt={m.original_filename}
                  className="w-full h-auto object-cover"
                  loading="lazy"
                />
                <span className="absolute inset-0 flex items-center justify-center bg-black/25 backdrop-blur-sm">
                  <span className="flex items-center justify-center w-12 h-12 rounded-full bg-white/80 text-ink-900 shadow-lg">
                    <Play size={22} fill="currentColor" />
                  </span>
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setLightbox(null)}
        >
          {lightbox.endsWith('.mp4') || lightbox.endsWith('.webm') ? (
            <video src={lightbox} controls className="max-h-[90vh] max-w-[90vw] rounded-2xl" />
          ) : (
            <img src={lightbox} alt="" className="max-h-[90vh] max-w-[90vw] rounded-2xl shadow-2xl" />
          )}
          <button
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            onClick={() => setLightbox(null)}
            aria-label="关闭"
          >
            <X size={22} />
          </button>
        </div>
      )}
    </>
  )
}