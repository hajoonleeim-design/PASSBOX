import { useParams } from 'react-router-dom'

export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  const params = useParams()
  return <section><p className="eyebrow">준비 중인 기능</p><h1>{title}</h1><p>{description}</p>{Object.keys(params).length > 0 && <p className="metadata">식별자: {Object.values(params).join(', ')}</p>}</section>
}
