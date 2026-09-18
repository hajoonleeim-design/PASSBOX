// label, 오류 문구, 입력 요소를 같은 모양으로 묶어 주는 폼 공통 컴포넌트입니다.
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
export function FormField({ label, helpText, error, children }: { label: string; helpText?: string; error?: string; children: ReactNode }) { return <label className="form-field"><span>{label}</span>{children}{error ? <small className="form-error" role="alert">{error}</small> : helpText ? <small>{helpText}</small> : null}</label> }
export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) { return <input className="form-control" {...props} /> }
export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) { return <select className="form-control" {...props} /> }
export function TextareaInput(props: TextareaHTMLAttributes<HTMLTextAreaElement>) { return <textarea className="form-control" {...props} /> }
