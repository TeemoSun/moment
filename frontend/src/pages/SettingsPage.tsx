import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { userApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

export default function SettingsPage() {
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [oldPwd, setOldPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [profileMsg, setProfileMsg] = useState('')
  const [pwdMsg, setPwdMsg] = useState('')
  const [pwdError, setPwdError] = useState('')
  const user = useAuthStore((s) => s.user)
  const updateUser = useAuthStore((s) => s.updateUser)
  const navigate = useNavigate()

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

  const changePassword = async () => {
    setPwdError(''); setPwdMsg('')
    if (newPwd.length < 8) { setPwdError('新密码至少8位'); return }
    if (newPwd !== confirmPwd) { setPwdError('两次输入的新密码不一致'); return }
    try {
      await userApi.changePassword(oldPwd, newPwd)
      setPwdMsg('密码修改成功')
      setOldPwd(''); setNewPwd(''); setConfirmPwd('')
    } catch (err: any) {
      setPwdError(err.response?.data?.detail || '修改失败')
    }
  }

  return (
    <div>
      {user && (
        <div className="card mb-4">
          <h2 className="font-medium mb-3">个人资料</h2>
          <label className="text-sm text-slate-500">昵称</label>
          <input
            className="input mt-1 mb-3"
            placeholder={user.display_name || user.username}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={64}
          />
          <label className="text-sm text-slate-500">简介</label>
          <textarea
            className="input mt-1 mb-3"
            placeholder={user.bio || '介绍一下自己'}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={500}
          />
          {profileMsg && <p className="text-sm text-brand-600 mb-2">{profileMsg}</p>}
          <button className="btn-primary" onClick={saveProfile}>保存资料</button>
        </div>
      )}

      <div className="card mb-4">
        <h2 className="font-medium mb-3">修改密码</h2>
        <input className="input mb-3" type="password" placeholder="旧密码" value={oldPwd} onChange={(e) => setOldPwd(e.target.value)} />
        <input className="input mb-3" type="password" placeholder="新密码（至少8位）" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} />
        <input className="input mb-3" type="password" placeholder="确认新密码" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)} />
        {pwdError && <p className="text-red-500 text-sm mb-2">{pwdError}</p>}
        {pwdMsg && <p className="text-brand-600 text-sm mb-2">{pwdMsg}</p>}
        <button className="btn-primary" onClick={changePassword} disabled={!oldPwd || !newPwd || !confirmPwd}>修改密码</button>
      </div>

      <button className="btn-ghost" onClick={() => navigate(-1)}>返回</button>
    </div>
  )
}