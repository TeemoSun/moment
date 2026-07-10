import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Video, Loader2 } from 'lucide-react'
import { Button, Card } from 'liquidify-react'
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
    <Card variant="glass" padded>
      <h2 className="font-semibold text-lg text-ink-800 mb-3">发布动态</h2>
      <textarea
        className="glass-input min-h-[120px] resize-y"
        placeholder="说点什么..."
        value={content}
        maxLength={2000}
        onChange={(e) => setContent(e.target.value)}
      />
      <div className="mt-3">
        <label className="text-sm text-ink-400">可见范围</label>
        <select
          className="glass-input glass-select mt-1"
          value={visibility}
          onChange={(e) => setVisibility(e.target.value as any)}
        >
          <option value="public">公开</option>
          <option value="friends">仅好友</option>
        </select>
      </div>
      <div className="mt-3">
        <label className="flex items-center justify-center gap-2 px-4 py-6 rounded-2xl border-2 border-dashed border-ink-100 text-ink-400 cursor-pointer hover:border-accent hover:text-accent transition-colors">
          <Upload size={20} />
          <span className="text-sm">点击或拖拽上传图片/视频</span>
          <input type="file" multiple accept="image/*,video/*" className="hidden" onChange={(e) => handleFiles(e.target.files)} />
        </label>
        {uploading && (
          <p className="text-sm text-ink-400 mt-1 flex items-center gap-1">
            <Loader2 size={14} className="animate-spin" /> 上传中...
          </p>
        )}
        {uploadedMedia.length > 0 && (
          <div className="grid grid-cols-3 gap-2 mt-2">
            {uploadedMedia.map((m) => (
              <div key={m.id} className="rounded-2xl overflow-hidden bg-ink-100 ring-1 ring-black/5 relative">
                {m.media_type === 'image' ? (
                  <img src={m.small_url || m.original_url || ''} alt="" className="w-full h-24 object-cover" />
                ) : (
                  <div className="w-full h-24 flex items-center justify-center text-ink-400 gap-1">
                    <Video size={20} /> 视频
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      <Button variant="filled" tone="accent" className="w-full mt-4" onClick={submit} disabled={uploading} loading={uploading}>
        发布
      </Button>
    </Card>
  )
}