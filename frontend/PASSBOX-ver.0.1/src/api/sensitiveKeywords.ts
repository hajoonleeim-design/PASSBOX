import { apiClient } from './client'

export type KeywordSeverity = 'HIGH' | 'MEDIUM'

export interface SensitiveKeyword {
  id: number
  keyword: string
  label: string
  severity: KeywordSeverity
  enabled: boolean
  createdAt: string
}

interface BackendKeyword {
  id: number
  keyword: string
  label: string
  severity: KeywordSeverity
  enabled: boolean
  created_at: string
}

const map = (row: BackendKeyword): SensitiveKeyword => ({
  id: row.id,
  keyword: row.keyword,
  label: row.label,
  severity: row.severity,
  enabled: row.enabled,
  createdAt: row.created_at,
})

const BASE = '/admin/sensitive-keywords'

export async function listSensitiveKeywords(): Promise<SensitiveKeyword[]> {
  const { data } = await apiClient.get<BackendKeyword[]>(BASE)
  return data.map(map)
}

export async function createSensitiveKeyword(input: { keyword: string; label: string; severity: KeywordSeverity }): Promise<SensitiveKeyword> {
  const { data } = await apiClient.post<BackendKeyword>(BASE, input)
  return map(data)
}

export async function updateSensitiveKeyword(id: number, input: Partial<Pick<SensitiveKeyword, 'label' | 'severity' | 'enabled'>>): Promise<SensitiveKeyword> {
  const { data } = await apiClient.patch<BackendKeyword>(`${BASE}/${id}`, input)
  return map(data)
}

export async function deleteSensitiveKeyword(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}
