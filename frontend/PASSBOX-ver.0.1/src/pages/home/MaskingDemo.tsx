import { useEffect, useState } from 'react'

// Every "after" below is the literal output of backend app.masking.mask_text() for the
// "before" sentence (with "블루문" registered as a confidential keyword). Keep it that way:
// this card claims to show what actually leaves the building.
const LINES = [
  { label: '전화번호', before: ['담당자 연락처: ', '010-1234-5678', ''], token: 'PHONE' },
  { label: '우회 표기', before: ['문의는 ', '공일공 구팔칠육 오사삼이', ' 로'], token: 'PHONE' },
  { label: '등록된 기밀 키워드', before: ['', '블루문', ' 사업 예산 3억 원 검토 요청'], token: 'CONFIDENTIAL_KEYWORD' },
  { label: '인증정보', before: ['연동 설정 ', 'api_key=sk-live-8f2Kx91QmZ', ''], token: 'SECRET' },
] as const

const STEP_MS = 1300
const HOLD_STEPS = 3

export function MaskingDemo() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => setStep((value) => (value + 1) % (LINES.length + HOLD_STEPS)), STEP_MS)
    return () => window.clearInterval(timer)
  }, [])

  const done = Math.min(step, LINES.length)

  return (
    <div className="mask-demo" aria-label="외부 AI로 보내기 전 민감정보를 가리는 과정 예시">
      <div className="mask-demo__head">
        <span><i aria-hidden="true" />외부 전송 전 자동 가림</span>
        <small>예시 문장 · 실제 마스킹 엔진 출력과 동일</small>
      </div>

      <div className="mask-demo__cols" aria-hidden="true">
        <span>기관 내부 원문</span>
        <span>외부 AI로 나가는 내용</span>
      </div>

      <ol className="mask-demo__list">
        {LINES.map((line, index) => {
          const state = index < done ? 'masked' : index === done ? 'scanning' : 'idle'
          const [pre, secret, post] = line.before
          return (
            <li key={line.label} className={`mask-demo__row is-${state}`}>
              <p className="mask-demo__before">
                {pre}<mark>{secret}</mark>{post}
              </p>
              <p className="mask-demo__after">
                {state === 'masked'
                  ? <>{pre}<code>[MASKED:{line.token}]</code>{post}</>
                  : <span className="mask-demo__pending">{state === 'scanning' ? '검사 중…' : '대기'}</span>}
              </p>
              <small className="mask-demo__tag">{line.label}</small>
            </li>
          )
        })}
      </ol>

      <div className="mask-demo__foot" aria-live="polite">
        <strong>{done}/{LINES.length}</strong> 건 가림 처리 · 가려진 부분은 기관 밖으로 나가지 않습니다
      </div>
    </div>
  )
}
