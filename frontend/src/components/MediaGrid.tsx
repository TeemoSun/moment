import { useState } from 'react'
import type { Media } from '@/api/types'

export function MediaGrid({ media }: { media: Media[] }) {
  const [lightbox, setLightbox] = useState<string | null>(null)
  if (!media.length) return null

  return (
    <>
      <div className={`grid gap-2 mt-3 ${media.length === 1 ? 'grid-cols-1' : 'grid-cols-2'}`}>
        {media.map((m) => (
          <div key={m.id} className="relative rounded-lg overflow-hidden bg-slate-100">
            {m.media_type === 'image' ? (
              <img
                src={m.small_url || m.original_url || ''}
                alt={m.original_filename}
                className="w-full h-auto object-cover cursor-pointer"
                loading="lazy"
                onClick={() => setLightbox(m.original_url || m.medium_url || m.small_url || '')}
              />
            ) : (
              <div className="relative">
                <img
                  src={m.small_url || ''}
                  alt={m.original_filename}
                  className="w-full h-auto object-cover cursor-pointer"
                  loading="lazy"
                  onClick={() => setLightbox(m.original_url || '')}
                />
                <span className="absolute inset-0 flex items-center justify-center text-white text-4xl bg-black/20">
                  ▶
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setLightbox(null)}
        >
          {lightbox.endsWith('.mp4') || lightbox.endsWith('.webm') ? (
            <video src={lightbox} controls className="max-h-[90vh] max-w-[90vw]" />
          ) : (
            <img src={lightbox} alt="" className="max-h-[90vh] max-w-[90vw]" />
          )}
          <button className="absolute top-4 right-4 text-white text-2xl" onClick={() => setLightbox(null)}>✕</button>
        </div>
      )}
    </>
  )
}