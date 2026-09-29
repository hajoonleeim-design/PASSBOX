import { useEffect, useState } from 'react'

// Hero 섹션의 "N2SF AI Clearance Pass" 티켓 UI입니다.
// 문서가 투입되면 PII MASKED -> TOKENIZED -> APPROVED 순서로 뱃지가 켜지는
// 시연용 루프 애니메이션을 보여줍니다(실제 검사 결과가 아닌 연출용 데모).
const STAGES = [
  { key: 'masked', label: 'PII MASKED' },
  { key: 'tokenized', label: 'TOKENIZED' },
  { key: 'approved', label: 'APPROVED' },
] as const

const STAGE_INTERVAL_MS = 1400

export function ClearancePassTicket() {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const id = window.setInterval(() => {
      setStage((current) => (current + 1) % (STAGES.length + 1))
    }, STAGE_INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div className="clearance-pass" role="img" aria-label="N2SF AI Clearance Pass: 문서가 마스킹, 토큰화, 승인 단계를 순서대로 거치는 데모">
      <div className="clearance-pass__top">
        <div className="clearance-pass__header">
          <span className="clearance-pass__eyebrow">N2SF AI CLEARANCE PASS</span>
          <span className="clearance-pass__pill">ZERO TRUST</span>
        </div>

        <div className="clearance-pass__fields">
          <div className="clearance-pass__field">
            <span>DOCUMENT</span>
            <strong>2026_보안업무_계획.hwp</strong>
          </div>
          <div className="clearance-pass__field">
            <span>ORIGIN</span>
            <strong>GOV NETWORK</strong>
          </div>
          <div className="clearance-pass__field">
            <span>DESTINATION</span>
            <strong>PUBLIC AI</strong>
          </div>
          <div className="clearance-pass__field">
            <span>CLASS</span>
            <strong className="clearance-pass__grade">S</strong>
          </div>
        </div>
      </div>

      <div className="clearance-pass__perforation" aria-hidden="true">
        <span className="clearance-pass__notch clearance-pass__notch--left" />
        <span className="clearance-pass__notch clearance-pass__notch--right" />
      </div>

      <div className="clearance-pass__bottom">
        <div className="clearance-pass__stages">
          {STAGES.map((item, index) => (
            <div key={item.key} className={`clearance-pass__stage ${stage > index ? 'is-active' : ''}`}>
              <i aria-hidden="true" />
              <span>{item.label}</span>
            </div>
          ))}
        </div>

        <div className="clearance-pass__footer">
          <span className="clearance-pass__barcode" aria-hidden="true" />
          <code className="clearance-pass__hash">SHA256 · A1F9C3E0…</code>
        </div>
      </div>
    </div>
  )
}
