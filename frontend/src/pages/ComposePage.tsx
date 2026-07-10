import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { postApi, mediaApi } from '@/api'
import type { Media } from '@/api/types'

export default function ComposePage() {
  const [content, setContent] = useState('')
  const [visibility, setVisibility] = useState<'public' | 'friends'>('public')
  const [uploadedMedia, setUploadedMedia] = useState<Media[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const MAX_IMAGE = 50 * 1024 * 1024
  const MAX_VIDEO = 200 * 1024 * 1024

  const handleFiles = async (selected: FileList | null) => {
    if (!selected || selected.length === 0) return
    setError('')
    const valid: File[] = []
    for (const f of Array.from(selected)) {
      if (f.type.startsWith('image/') && f.size > MAX_IMAGE) {
        setError(`图片 ${f.name} 超过50MB限制`)
        continue
      }
      if (f.type.startsWith('video/') && f.size > MAX_VIDEO) {
        setError(`视频 ${f.name} 超过200MB限制`)
        continue
      }
      valid.push(f)
    }
    if (valid.length === 0) return

    setUploadedMedia((prev) => [...prev])
    setUploading(true)
    for (const f of valid) {
      try {
        const m = await mediaApi.upload(f)
        setUploadedMedia((prev) => [...prev, m])
      } catch (err: any) {
        setError(`上传 ${f.name} 失败: ${err.response?.data?.detail || err.message}`)
      }
    }
    setUploading(false)
  }

  const submit = async () => {
    setError('')
    if (!content.trim() && uploadedMedia.length === 0) {
      setError('请输入内容或上传媒体')
      return
    }
    try {
      await postApi.create({
        content: content.trim(),
        media_ids: uploadedMedia.map((m) => m.id),
        visibility,
      })
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || '发布失败')
    }
  }

  return (
    <div className="card">
      <h2 className="font-medium mb-3">发布动态</h2>
      <textarea
        className="input min-h-[120px] resize-y"
        placeholder="说点什么..."
        value={content}
        maxLength={2000}
        onChange={(e) => setContent(e.target.value)}
      />
      <div className="mt-3">
        <label className="text-sm text-slate-500">可见范围</label>
        <select className="input mt-1" value={visibility} onChange={(e) => setVisibility(e.target.value as any)}>
          <option value="public">公开</option>
          <option value="friends">仅好友</option>
        </select>
      </div>
      <div className="mt-3">
        <input type="file" multiple accept="image/*,video/*" onChange={(e) => handleFiles(e.target.files)} />
        {uploading && <p className="text-sm text-slate-500 mt-1">上传中...</p>}
        {uploadedMedia.length > 0 && (
          <div className="grid grid-cols-3 gap-2 mt-2">
            {uploadedMedia.map((m) => (
              <div key={m.id} className="rounded-lg overflow-hidden bg-slate-100">
                {m.media_type === 'image' ? (
                  <img src={m.small_url || m.original_url || ''} alt="" className="w-full h-24 object-cover" />
                ) : (
                  <div className="w-full h-24 flex items-center justify-center text-slate-400">视频</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      <button className="btn-primary w-full mt-4" onClick={submit} disabled={uploading}>
        发布
      </button>
    </div>
  )
}