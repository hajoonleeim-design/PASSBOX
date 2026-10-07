import { useEffect, useState } from 'react'

// 화면 중앙에 가장 가까운 섹션을 "현재 섹션"으로 추적합니다. 하단 독(dock)
// 내비게이션에서 지금 보고 있는 구간을 강조하는 데 씁니다. IntersectionObserver
// 대신 스크롤 이벤트 + getBoundingClientRect로 직접 계산합니다(useScrollStages와
// 같은 방식) — 환경에 따라 레이아웃 변경 없이 리플로우만으로 안정적으로 동작합니다.
export function useActiveSection(ids: string[]) {
  const [active, setActive] = useState(ids[0] ?? '')

  useEffect(() => {
    const elements = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null)
    if (elements.length === 0) return

    const onScroll = () => {
      const center = window.innerHeight / 2
      let closestId = elements[0].id
      let closestDistance = Infinity
      for (const el of elements) {
        const rect = el.getBoundingClientRect()
        if (rect.top <= center && rect.bottom >= center) {
          closestId = el.id
          closestDistance = 0
          break
        }
        const distance = rect.top > center ? rect.top - center : center - rect.bottom
        if (distance < closestDistance) {
          closestDistance = distance
          closestId = el.id
        }
      }
      setActive(closestId)
    }

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [ids.join(',')])

  return active
}
