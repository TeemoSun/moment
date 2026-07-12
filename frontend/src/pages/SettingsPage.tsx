import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, Check, Camera } from 'lucide-react'
import { Button, Card } from 'liquidify-react'
import { userApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { Avatar } from '@/components/Avatar'

export default function SettingsPage() {
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [oldPwd, setOldPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [profileMsg, setProfileMsg] = useState('')
  const [avatarMsg, setAvatarMsg] = useState('')
  const [avatarError, setAvatarError] = useState('')
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [pwdMsg, setPwdMsg] = useState('')
  const [pwdError, setPwdError] = useState('')
  const user = useAuthStore((s) => s.user)
  const updateUser = useAuthStore((s) => s.updateUser)
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)

  const saveProfile = async () => {
    setProfileMsg('')
    try {
      const updated = await userApi.updateMe({
        display_name: displayName || undefined,
        bio: bio || undefined,
      })
      updateUser(updated)
      setProfileMsg('资料已保存')
    } catch (err: any) {
      setProfileMsg(err.response?.data?.detail || '保存失败')
    }
  }

  const onAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setAvatarError('')
    setAvatarMsg('')
    setAvatarUploading(true)
    try {
      const updated = await userApi.uploadAvatar(file)
      updateUser(updated)
      setAvatarMsg('头像已更新')
    } catch (err: any) {
      setAvatarError(err.response?.data?.detail || '头像上传失败')
    } finally {
      setAvatarUploading(false)
    }
  }

  const changePassword = async () => {
    setPwdError('')
    setPwdMsg('')
    if (newPwd.length < 8) {
      setPwdError('新密码至少8位')
      return
    }
    if (newPwd !== confirmPwd) {
      setPwdError('两次输入的新密码不一致')
      return
    }
    try {
      await userApi.changePassword(oldPwd, newPwd)
      setPwdMsg('密码修改成功')
      setOldPwd('')
      setNewPwd('')
      setConfirmPwd('')
    } catch (err: any) {
      setPwdError(err.response?.data?.detail || '修改失败')
    }
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Button variant="plain" tone="neutral" size="compact" onClick={() => navigate(-1)} icon={<ChevronLeft size={18} />} aria-label="返回" />
        <h1 className="text-lg font-bold text-ink-800">设置</h1>
      </div>

      {user && (
        <Card variant="glass" padded className="mb-4">
          <h2 className="font-semibold text-ink-800 mb-3">个人资料</h2>
          <div className="flex items-center gap-4 mb-4">
            <div className="relative group cursor-pointer" onClick={() => fileRef.current?.click()}>
              <Avatar user={user} size={64} />
              <div className="absolute inset-0 rounded-full bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <Camera size={20} className="text-white" />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <Button variant="filled" tone="accent" size="compact" onClick={() => fileRef.current?.click()} disabled={avatarUploading}>
                {avatarUploading ? '上传中...' : '更换头像'}
              </Button>
              {avatarMsg && <p className="text-sm text-accent flex items-center gap-1"><Check size={14} /> {avatarMsg}</p>}
              {avatarError && <p className="text-sm text-red-500">{avatarError}</p>}
            </div>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onAvatarChange} />
          </div>
          <label className="text-sm text-ink-400">昵称</label>
          <input
            className="glass-input mt-1 mb-3"
            placeholder={user.display_name || user.username}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={64}
          />
          <label className="text-sm text-ink-400">简介</label>
          <textarea
            className="glass-input mt-1 mb-3 min-h-[80px] resize-y"
            placeholder={user.bio || '介绍一下自己'}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={500}
          />
          {profileMsg && <p className="text-sm text-accent mb-2 flex items-center gap-1"><Check size={14} /> {profileMsg}</p>}
          <Button variant="filled" tone="accent" onClick={saveProfile}>
            保存资料
          </Button>
        </Card>
      )}

      <Card variant="glass" padded className="mb-4">
        <h2 className="font-semibold text-ink-800 mb-3">修改密码</h2>
        <input className="glass-input mb-3" type="password" placeholder="旧密码" value={oldPwd} onChange={(e) => setOldPwd(e.target.value)} />
        <input className="glass-input mb-3" type="password" placeholder="新密码（至少8位）" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} />
        <input className="glass-input mb-3" type="password" placeholder="确认新密码" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)} />
        {pwdError && <p className="text-red-500 text-sm mb-2">{pwdError}</p>}
        {pwdMsg && <p className="text-accent text-sm mb-2 flex items-center gap-1"><Check size={14} /> {pwdMsg}</p>}
        <Button variant="filled" tone="accent" onClick={changePassword} disabled={!oldPwd || !newPwd || !confirmPwd}>
          修改密码
        </Button>
      </Card>
    </div>
  )
}