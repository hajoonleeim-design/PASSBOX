import { useState, type FormEvent } from 'react'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { FormField, TextInput } from '../../components/common/FormControls'
import { useAuth } from '../../hooks/useAuth'
import { changePassword } from '../../api/auth'

const passwordHelp = '영문, 숫자, 특수문자를 포함한 12자 이상의 비밀번호를 사용하세요.'

export function AccountPage() {
  const { session } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formError, setFormError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [success, setSuccess] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    setSubmitError('')
    setSuccess(false)

    if (!currentPassword) {
      setFormError('현재 비밀번호를 입력하세요.')
      return
    }
    if (newPassword.length < 12) {
      setFormError('새 비밀번호는 12자 이상이어야 합니다.')
      return
    }
    if (newPassword !== confirmPassword) {
      setFormError('새 비밀번호와 확인 값이 일치하지 않습니다.')
      return
    }
    if (currentPassword === newPassword) {
      setFormError('현재 비밀번호와 다른 비밀번호를 사용하세요.')
      return
    }

    setIsSubmitting(true)
    try {
      await changePassword({ currentPassword, newPassword })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setSuccess(true)
    } catch {
      setSubmitError('비밀번호를 변경하지 못했습니다. 현재 비밀번호를 확인하고 다시 시도하세요.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return <section className="account-page">
    <p className="eyebrow">ACCOUNT SECURITY</p>
    <div className="page-title-row">
      <div>
        <h1>계정 보안</h1>
        <p>로그인 계정과 세션 정보를 안전하게 관리합니다.</p>
      </div>
    </div>

    <div className="account-grid">
      <Card>
        <h2>현재 계정</h2>
        <dl className="info-list account-info-list">
          <div><dt>사용자</dt><dd>{session?.displayName}</dd></div>
          <div><dt>역할</dt><dd>{session?.role}</dd></div>
          <div><dt>기관</dt><dd>{session?.institutionName}</dd></div>
        </dl>
      </Card>

      <Card>
        <h2>비밀번호 변경</h2>
        <p className="account-card-description">정기적으로 비밀번호를 변경하고 다른 서비스와 같은 비밀번호는 사용하지 마세요.</p>
        <form onSubmit={handleSubmit} noValidate>
          <FormField label="현재 비밀번호" error={formError}>
            <TextInput type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
          </FormField>
          <FormField label="새 비밀번호" helpText={passwordHelp}>
            <TextInput type="password" autoComplete="new-password" minLength={12} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </FormField>
          <FormField label="새 비밀번호 확인">
            <TextInput type="password" autoComplete="new-password" minLength={12} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
          </FormField>
          {submitError && <Alert variant="danger" title="변경 실패">{submitError}</Alert>}
          {success && <Alert variant="success" title="변경 완료">비밀번호가 안전하게 변경되었습니다.</Alert>}
          <div className="form-actions">
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? '변경 중...' : '비밀번호 변경'}</Button>
          </div>
        </form>
      </Card>
    </div>
  </section>
}
