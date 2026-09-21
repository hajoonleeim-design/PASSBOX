// 아이디와 비밀번호를 받아 로그인하고, 성공하면 원래 가려 했던 화면으로 이동합니다.
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../../components/common/Button'
import { FormField, TextInput } from '../../components/common/FormControls'
import { Alert } from '../../components/common/Alert'
import { useAuth } from '../../hooks/useAuth'

export function LoginPage() {
  const { login } = useAuth(); const navigate = useNavigate(); const location = useLocation()
  const [username, setUsername] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [isSubmitting, setIsSubmitting] = useState(false)
  async function handleSubmit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setError(''); setIsSubmitting(true); try { await login({ username, password }); navigate((location.state as { from?: string } | null)?.from ?? '/', { replace: true }) } catch (reason) { setError(reason instanceof Error ? reason.message : '로그인에 실패했습니다.') } finally { setIsSubmitting(false) } }
  return <><p className="eyebrow">기관용 보안 서비스</p><h1>PASSBOX 로그인</h1><p>기관 계정으로 로그인해 문서 보안 검사와 안전한 AI 업무를 이용하세요.</p><Alert variant="info" title="기관 자동 연결">개발 환경에서는 테스트 기관으로 자동 연결됩니다. 운영 환경에서는 인증 서버의 기관 매핑 결과를 사용합니다.</Alert><form onSubmit={handleSubmit}><FormField label="사용자 ID"><TextInput value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" required /></FormField><FormField label="비밀번호"><TextInput type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="off" required /></FormField>{error && <Alert variant="danger" title="로그인 실패">{error}</Alert>}<Button type="submit" disabled={isSubmitting}>{isSubmitting ? '로그인 중' : '로그인'}</Button></form><Alert variant="warning" title="보안 안내">비밀번호와 인증정보는 브라우저 저장소에 저장하지 않습니다.</Alert><small>개발용 테스트 인증입니다. 운영 환경에서는 승인된 인증 서버를 연결해야 합니다.</small></>
}
