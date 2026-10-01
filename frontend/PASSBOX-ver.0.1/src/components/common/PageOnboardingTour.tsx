import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from './Button'

export type OnboardingTourStep = {
  id: string
  target: string
  title: string
  description: string
  calloutAlign?: 'target' | 'center'
}

type HighlightRect = { top: number; left: number; width: number; height: number }

type PageOnboardingTourProps = {
  storageKey: string
  steps: OnboardingTourStep[]
  onActiveStepChange?: (stepIndex: number | null) => void
  targetReadyKey?: number | null
  markerNumber?: number
  initiallyOpen?: boolean
  calloutPlacement?: 'target' | 'bottom'
}

const readCompleted = (storageKey: string) => {
  try {
    return window.localStorage.getItem(storageKey) === 'completed'
  } catch {
    return false
  }
}

export function PageOnboardingTour({ storageKey, steps, onActiveStepChange, targetReadyKey, markerNumber, initiallyOpen = false, calloutPlacement = 'target' }: PageOnboardingTourProps) {
  const [isOpen, setIsOpen] = useState(() => initiallyOpen || !readCompleted(storageKey))
  const [stepIndex, setStepIndex] = useState(0)
  const [targetRect, setTargetRect] = useState<HighlightRect | null>(null)
  const [calloutHeight, setCalloutHeight] = useState(220)
  const [calloutWidth, setCalloutWidth] = useState(336)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const calloutRef = useRef<HTMLElement>(null)
  const ignoreNextScreenClick = useRef(false)
  const transitionTimer = useRef<number | null>(null)
  const isTransitioningRef = useRef(false)
  const step = steps[stepIndex]

  const complete = useCallback(() => {
    try {
      window.localStorage.setItem(storageKey, 'completed')
    } catch {
      // Storage can be unavailable in private or restricted browser contexts.
    }
    setIsOpen(false)
  }, [storageKey])

  const advance = useCallback(() => {
    if (isTransitioningRef.current) return
    isTransitioningRef.current = true
    setIsTransitioning(true)
    transitionTimer.current = window.setTimeout(() => {
      if (stepIndex === steps.length - 1) complete()
      else {
        setTargetRect(null)
        setStepIndex((current) => current + 1)
      }
      isTransitioningRef.current = false
      setIsTransitioning(false)
    }, 220)
  }, [complete, stepIndex, steps.length])

  useEffect(() => () => {
    if (transitionTimer.current !== null) window.clearTimeout(transitionTimer.current)
  }, [])

  useEffect(() => {
    const callout = calloutRef.current
    if (!isOpen || !callout) return undefined
    const measure = () => {
      const rect = callout.getBoundingClientRect()
      setCalloutHeight(rect.height)
      setCalloutWidth(rect.width)
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(callout)
    return () => observer.disconnect()
  }, [isOpen, stepIndex])

  useEffect(() => {
    if (!isOpen || !step) return undefined

    const target = document.querySelector<HTMLElement>(step.target)
    if (!target) return undefined

    const updateTargetRect = () => {
      const rect = target.getBoundingClientRect()
      setTargetRect({ top: rect.top, left: rect.left, width: rect.width, height: rect.height })
    }

    const advanceOnScreenClick = (event: MouseEvent) => {
      if (ignoreNextScreenClick.current) {
        ignoreNextScreenClick.current = false
        return
      }
      const clickedElement = event.target instanceof Element ? event.target : null
      if (clickedElement?.closest('[data-onboarding-tour-control]')) return
      advance()
    }

    const stepMarker = document.createElement('span')
    stepMarker.className = 'onboarding-tour-target__step'
    stepMarker.setAttribute('aria-hidden', 'true')
    stepMarker.textContent = String(markerNumber ?? stepIndex + 1)

    target.classList.add('onboarding-tour-target')
    target.setAttribute('data-onboarding-step', String(stepIndex + 1))
    target.append(stepMarker)
    target.scrollIntoView({
      block: 'center',
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    })
    updateTargetRect()

    window.addEventListener('resize', updateTargetRect)
    window.addEventListener('scroll', updateTargetRect, true)
    document.addEventListener('click', advanceOnScreenClick)

    return () => {
      target.classList.remove('onboarding-tour-target')
      target.removeAttribute('data-onboarding-step')
      stepMarker.remove()
      window.removeEventListener('resize', updateTargetRect)
      window.removeEventListener('scroll', updateTargetRect, true)
      document.removeEventListener('click', advanceOnScreenClick)
    }
  }, [advance, isOpen, markerNumber, step, stepIndex, targetReadyKey])

  useEffect(() => {
    const restart = (event: Event) => {
      const requestedStorageKey = (event as CustomEvent<string>).detail
      if (requestedStorageKey !== storageKey) return
      try {
        window.localStorage.removeItem(storageKey)
      } catch {
        // Restart still works for the current page when storage is unavailable.
      }
      // The click on "사용 안내 다시 보기" must not also advance the newly opened tour.
      ignoreNextScreenClick.current = true
      if (transitionTimer.current !== null) window.clearTimeout(transitionTimer.current)
      isTransitioningRef.current = false
      setIsTransitioning(false)
      setStepIndex(0)
      setTargetRect(null)
      setIsOpen(true)
    }

    window.addEventListener('passbox:onboarding-restart', restart)
    return () => window.removeEventListener('passbox:onboarding-restart', restart)
  }, [storageKey])

  useEffect(() => {
    onActiveStepChange?.(isOpen ? stepIndex : null)
  }, [isOpen, onActiveStepChange, stepIndex])

  if (!isOpen || !step) return null

  const gap = 12
  const belowTarget = targetRect ? targetRect.top + targetRect.height + gap : 96
  const aboveTarget = targetRect ? targetRect.top - calloutHeight - gap : 96
  const hasRoomBelow = targetRect !== null && belowTarget + calloutHeight <= window.innerHeight - 16
  const hasRoomAbove = targetRect !== null && aboveTarget >= 16
  const calloutTop = targetRect
    ? hasRoomBelow
      ? belowTarget
      : hasRoomAbove
        ? aboveTarget
        : Math.max(16, Math.min(belowTarget, window.innerHeight - calloutHeight - 16))
    : 96
  const maxCalloutLeft = Math.max(16, window.innerWidth - calloutWidth - 16)
  const calloutLeft = step.calloutAlign === 'center'
    ? Math.max(16, Math.min((window.innerWidth - calloutWidth) / 2, maxCalloutLeft))
    : targetRect
      ? Math.max(16, Math.min(targetRect.left, maxCalloutLeft))
      : 24

  return (
    <div className={`onboarding-tour ${calloutPlacement === 'bottom' ? 'onboarding-tour--bottom' : ''}`.trim()} aria-live="polite">
      <aside ref={calloutRef} key={stepIndex} className={`onboarding-tour__callout ${isTransitioning ? 'onboarding-tour__callout--leaving' : ''}`.trim()} aria-label={`온보딩 ${stepIndex + 1}단계`} data-onboarding-tour-control style={{ top: calloutTop, left: calloutLeft }}>
        <p>시작 안내 · {stepIndex + 1} / {steps.length}</p>
        <h2>{step.title}</h2>
        <span>{step.description}</span>
        <div>
          <small>화면을 클릭하거나 다음 안내를 누르면 다음 단계로 이동합니다.</small>
          <span className="onboarding-tour__actions">
            <Button size="sm" variant="ghost" onClick={complete}>건너뛰기</Button>
            <Button size="sm" onClick={advance}>{stepIndex === steps.length - 1 ? '완료' : '다음 안내'}</Button>
          </span>
        </div>
      </aside>
    </div>
  )
}
