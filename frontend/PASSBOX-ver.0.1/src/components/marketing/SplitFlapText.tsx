import { useEffect, useState } from 'react'

// 공항 출발 안내판(Split-flap) 스타일 텍스트 셔플러입니다.
// 각 글자 칸이 왼쪽부터 순서대로 무작위 글자를 빠르게 훑다가 실제 글자에 멈춥니다.
const FLAP_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/·-'
const TICK_MS = 40
const SETTLE_STAGGER_TICKS = 2

type SplitFlapTextProps = {
  text: string
  className?: string
  triggerOnHover?: boolean
  autoPlay?: boolean
}

function randomChar() {
  return FLAP_CHARS[Math.floor(Math.random() * FLAP_CHARS.length)]
}

export function SplitFlapText({ text, className = '', triggerOnHover = true, autoPlay = true }: SplitFlapTextProps) {
  const [display, setDisplay] = useState<string[]>(() => text.split(''))
  const [playCount, setPlayCount] = useState(autoPlay ? 1 : 0)

  useEffect(() => {
    if (playCount === 0) {
      setDisplay(text.split(''))
      return
    }
    const chars = text.split('')
    let frame = 0
    const totalTicks = chars.length * SETTLE_STAGGER_TICKS + 8
    const id = window.setInterval(() => {
      frame += 1
      setDisplay(chars.map((ch, index) => {
        if (ch === ' ') return ' '
        const settleAt = index * SETTLE_STAGGER_TICKS + 6
        return frame >= settleAt ? ch : randomChar()
      }))
      if (frame >= totalTicks) window.clearInterval(id)
    }, TICK_MS)
    return () => window.clearInterval(id)
  }, [text, playCount])

  return (
    <span
      className={`split-flap ${className}`}
      aria-label={text}
      onMouseEnter={triggerOnHover ? () => setPlayCount((count) => count + 1) : undefined}
    >
      {display.map((ch, index) => (
        <span key={index} className="split-flap__cell" aria-hidden="true">
          {ch === ' ' ? ' ' : ch}
        </span>
      ))}
    </span>
  )
}
