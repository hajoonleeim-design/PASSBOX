import { useEffect, useRef, useState } from 'react'

// 에스원 쇼룸처럼 한 구간을 스크롤하는 동안 화면은 고정된 채 내용만
// 단계별로 바뀌는 효과입니다. wrapper를 count*100vh 높이로 두고,
// 그 안의 sticky 프레임이 뷰포트에 붙어 있는 동안 스크롤 진행률로
// 현재 단계를 계산합니다. 네이티브 스크롤 이벤트만 읽고 막지 않으므로
// 트랙패드·키보드·터치 스크롤을 전혀 가로채지 않습니다.
export function useScrollStages<T extends HTMLElement>(count: number) {
  const wrapperRef = useRef<T>(null)
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const el = wrapperRef.current
    if (!el || count <= 1) return

    const onScroll = () => {
      const { start, total } = pinnedRange(el)
      const progress = total > 0 ? Math.min(1, Math.max(0, (start - el.getBoundingClientRect().top) / total)) : 0
      setStage(Math.min(count - 1, Math.floor(progress * count)))
    }

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [count])

  const scrollToStage = (index: number) => {
    const el = wrapperRef.current
    if (!el) return
    const { start, total } = pinnedRange(el)
    const targetProgress = (index + 0.5) / count
    const targetY = window.scrollY + el.getBoundingClientRect().top - start + targetProgress * total
    window.scrollTo({ top: targetY, behavior: 'smooth' })
  }

  return { wrapperRef, stage, scrollToStage }
}

// The sticky frame (first child) pins at its CSS `top` offset and stays pinned while the
// wrapper scrolls by (wrapper height - frame height).
function pinnedRange(el: HTMLElement) {
  const frame = el.firstElementChild as HTMLElement | null
  const frameHeight = frame?.offsetHeight ?? window.innerHeight
  const start = frame ? parseFloat(getComputedStyle(frame).top) || 0 : 0
  return { start, total: el.offsetHeight - frameHeight }
}
