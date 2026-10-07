import { useEffect, useRef } from 'react'

// 랜딩·로그인·홈 공통 커스텀 커서입니다. 패스박스 큐브 모양이 마우스를
// 그대로 따라다니기만 합니다(둘러싸던 스캐너 브래킷 프레임은 제거). 마우스가
// 있는 데스크톱(hover:hover + pointer:fine)에서만 마운트되어 터치 기기에는
// 영향이 없습니다.
export function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return

    const dot = dotRef.current
    if (!dot) return

    let mouseX = window.innerWidth / 2
    let mouseY = window.innerHeight / 2
    dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0)`

    const onMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
      dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0)`
    }

    document.body.classList.add('has-pb-cursor')
    window.addEventListener('mousemove', onMove)

    return () => {
      document.body.classList.remove('has-pb-cursor')
      window.removeEventListener('mousemove', onMove)
    }
  }, [])

  return (
    <div ref={dotRef} className="pb-cursor-dot" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="18" height="18">
        <path d="M12 2 21 7l-9 5-9-5 9-5Z" fill="#2a2d31" stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="M3 7l9 5v10L3 17V7Z" fill="#050607" stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="m12 12 9-5v10l-9 5V12Z" fill="#3b82f6" stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
    </div>
  )
}
