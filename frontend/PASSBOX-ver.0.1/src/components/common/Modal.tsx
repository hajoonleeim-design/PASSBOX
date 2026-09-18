// 화면 위에 띄우는 공통 모달과, 확인/취소용 ConfirmDialog를 제공합니다.
import { useEffect, useRef, type PropsWithChildren } from 'react'
import { Button } from './Button'

export function Modal({ children, title, onClose }: PropsWithChildren<{ title: string; onClose?: () => void }>) {
  const dialogRef = useRef<HTMLElement>(null)
  const onCloseRef = useRef(onClose)
  useEffect(() => { onCloseRef.current = onClose }, [onClose])
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialogRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { onCloseRef.current?.(); return }
      if (event.key !== 'Tab') return
      const dialog = dialogRef.current
      if (!dialog) return
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
      if (focusable.length === 0) { event.preventDefault(); dialog.focus(); return }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus()
    }
  }, [])
  const close = () => onCloseRef.current?.()
  return <div className="modal-backdrop" role="presentation" onMouseDown={close}><section ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title} className="modal" onMouseDown={(event) => event.stopPropagation()}><div className="modal__header"><h2>{title}</h2>{onClose && <button type="button" className="icon-button" aria-label="닫기" onClick={close}>×</button>}</div>{children}</section></div>
}

export function ConfirmDialog({ title, message, onClose, onConfirm, confirmLabel = '확인', isConfirming = false }: { title: string; message: string; onClose?: () => void; onConfirm?: () => void; confirmLabel?: string; isConfirming?: boolean }) {
  return <Modal title={title} onClose={onClose}><p>{message}</p><div className="modal-actions"><Button variant="ghost" onClick={onClose}>닫기</Button>{onConfirm && <Button variant="danger" onClick={onConfirm} disabled={isConfirming}>{isConfirming ? '처리 중' : confirmLabel}</Button>}</div></Modal>
}
