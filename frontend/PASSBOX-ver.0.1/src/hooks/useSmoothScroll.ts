import { useEffect } from 'react'

// 휠 스크롤을 완만하게 보간해 에스원 쇼룸류 사이트 특유의 "부드럽게 미끄러지는"
// 스크롤감을 흉내 냅니다. 마우스가 있는 데스크톱에서만 동작하고, 터치 기기나
// prefers-reduced-motion 환경에서는 그대로 네이티브 스크롤을 씁니다.
export function useSmoothScroll(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    let current = window.scrollY
    let target = window.scrollY
    let raf = 0

    const maxScroll = () => document.documentElement.scrollHeight - window.innerHeight

    const step = () => {
      current += (target - current) * 0.09
      if (Math.abs(target - current) < 0.5) {
        current = target
        window.scrollTo(0, current)
        raf = 0
        return
      }
      window.scrollTo(0, current)
      raf = requestAnimationFrame(step)
    }

    const insideScrollable = (node: EventTarget | null) => {
      let el = node as HTMLElement | null
      while (el && el !== document.body) {
        const oy = getComputedStyle(el).overflowY
        if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight) return true
        el = el.parentElement
      }
      return false
    }

    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || insideScrollable(e.target)) return
      e.preventDefault()
      if (!raf) {
        // 휠 애니메이션이 멈춰 있던 사이 스크롤바 드래그 등으로 위치가
        // 바뀌었을 수 있으니, 새 입력이 시작될 때 실제 위치에서 다시 맞춘다.
        current = window.scrollY
        target = window.scrollY
      }
      target = Math.min(Math.max(target + e.deltaY * 0.9, 0), maxScroll())
      if (!raf) raf = requestAnimationFrame(step)
    }

    const onResize = () => {
      target = Math.min(target, maxScroll())
    }

    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('resize', onResize)

    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('resize', onResize)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [enabled])
}
