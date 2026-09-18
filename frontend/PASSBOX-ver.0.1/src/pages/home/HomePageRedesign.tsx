import { useNavigate } from 'react-router-dom'
import { Badge } from '../../components/common/Badge'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { useAuth } from '../../hooks/useAuth'

const signals = [
  { label: 'Policy engine', value: 'ONLINE', detail: 'LOCAL-TEMPLATE-v1', tone: 'healthy' },
  { label: 'Gateway mode', value: 'MOCK', detail: 'Safe local testing', tone: 'info' },
  { label: 'Data boundary', value: 'PRIVATE', detail: 'Original content withheld', tone: 'healthy' },
  { label: 'Approval queue', value: 'READY', detail: 'S-grade review enabled', tone: 'warning' },
] as const

const flow = [
  ['01', 'Upload & inspect', 'Quarantine, hash, and validate the file', 'SECURE'],
  ['02', 'Classify C / S / O', 'Apply the policy grade with human confirmation', 'CONTROLLED'],
  ['03', 'Gateway decision', 'Mask, approve, transmit, and post-inspect', 'AUDITED'],
] as const

export function HomePageRedesign() {
  const { session } = useAuth()
  const navigate = useNavigate()

  return (
    <section className="home-page" aria-labelledby="home-title">
      <div className="home-hero card">
        <div>
          <p className="eyebrow"><span className="signal-dot" /> PASSBOX / SECURITY OPERATIONS</p>
          <h1 id="home-title">안전한 AI 업무를 위한<br /><span>보안 관제 허브</span></h1>
          <p>
            문서와 프롬프트가 외부 AI로 넘어가기 전에 정책, 마스킹, 승인, 사후 검사를 한 흐름으로 관리합니다.
          </p>
          <div className="home-hero__actions">
            <Button size="lg" onClick={() => navigate('/upload')}>문서 분석 시작</Button>
            <Button size="lg" variant="secondary" onClick={() => navigate('/chat')}>안전한 AI 대화</Button>
          </div>
        </div>
        <div className="home-hero__visual" aria-hidden="true">
          <div className="security-orbit">
            <div className="security-orbit__core">PB</div>
            <span className="security-orbit__label">PROTECTED</span>
          </div>
        </div>
      </div>

      <div className="home-signal-grid" aria-label="보안 시스템 상태">
        {signals.map((signal) => (
          <Card key={signal.label} className={`signal-card signal-card--${signal.tone}`}>
            <span className="signal-card__label">{signal.label}</span>
            <strong>{signal.value}</strong>
            <small>{signal.detail}</small>
          </Card>
        ))}
      </div>

      <div className="home-workspace-grid">
        <Card>
          <div className="section-heading">
            <div>
              <p className="eyebrow">SECURITY FLOW</p>
              <h2>보안 처리 흐름</h2>
              <p>모든 AI 요청은 아래 세 단계를 거쳐 추적 가능한 기록으로 남습니다.</p>
            </div>
            <Badge variant="success">POLICY ENFORCED</Badge>
          </div>
          <div className="home-flow">
            {flow.map(([number, title, description, status]) => (
              <div className="home-flow__item" key={number}>
                <span className="home-flow__number">{number}</span>
                <div><strong>{title}</strong><small>{description}</small></div>
                <Badge variant={status === 'AUDITED' ? 'info' : 'success'}>{status}</Badge>
              </div>
            ))}
          </div>
        </Card>

        <div className="home-side-stack">
          <Card>
            <p className="eyebrow">CURRENT SESSION</p>
            <h2>{session?.displayName ?? 'PASSBOX 사용자'}님, 환영합니다.</h2>
            <p>현재 계정은 <strong>{session?.institutionName ?? '기관'}</strong>의 <strong>{session?.role ?? 'USER'}</strong> 권한으로 연결되어 있습니다.</p>
            <div className="security-summary">
              <div className="security-summary__score">OK</div>
              <div><strong>보안 세션 정상</strong><br /><small>정책 검증과 감사 기록이 활성화되어 있습니다.</small></div>
            </div>
          </Card>
          <Card>
            <p className="eyebrow">QUICK ACCESS</p>
            <h2>검토가 필요한 작업이 있나요?</h2>
            <p>문서 분석을 시작하거나 승인 대기 중인 요청을 확인할 수 있습니다.</p>
            <div className="form-actions">
              <Button size="sm" variant="ghost" onClick={() => navigate('/approvals')}>승인 요청 보기</Button>
              <Button size="sm" variant="ghost" onClick={() => navigate('/audit/mock-request')}>감사 기록 조회</Button>
            </div>
          </Card>
        </div>
      </div>
    </section>
  )
}
