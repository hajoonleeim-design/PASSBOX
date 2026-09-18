import type { AuditActor, AuditEvidence, AuditPdfResult, AuditRecord } from '../types/audit'
const useMock = import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL
export async function getAudit(requestId: string, actor: AuditActor): Promise<AuditRecord> { if (useMock) { const { mockGetAudit } = await import('../mocks/audit'); return mockGetAudit(requestId, actor) } throw new Error('승인된 Audit API 명세가 아직 연결되지 않았습니다.') }
export async function getAuditEvidence(requestId: string, actor: AuditActor): Promise<AuditEvidence> { if (useMock) { const { mockGetAuditEvidence } = await import('../mocks/audit'); return mockGetAuditEvidence(requestId, actor) } throw new Error('승인된 Audit Evidence API 명세가 아직 연결되지 않았습니다.') }
export async function generateAuditPdf(requestId: string, actor: AuditActor): Promise<AuditPdfResult> { if (useMock) { const { mockGenerateAuditPdf } = await import('../mocks/audit'); return mockGenerateAuditPdf(requestId, actor) } throw new Error('승인된 PDF API 명세가 아직 연결되지 않았습니다.') }
// 감사 기록 조회와 PDF 생성 요청을 담당하는 API 계층입니다.
