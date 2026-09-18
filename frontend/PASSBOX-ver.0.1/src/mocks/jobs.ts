import type { AnalysisJob, CreateJobInput, JobStatus } from '../types/security'

const progressStates: Array<{ status: JobStatus; progress: number; step: string }> = [
  { status: 'RECEIVED', progress: 5, step: '접수' }, { status: 'INSPECTING', progress: 16, step: '검사' }, { status: 'PARSING', progress: 30, step: '파싱' }, { status: 'DETECTING', progress: 45, step: '탐지' }, { status: 'MASKING', progress: 62, step: '마스킹' }, { status: 'WAITING_APPROVAL', progress: 72, step: '승인대기' }, { status: 'TRANSMITTING', progress: 82, step: '전송' }, { status: 'POST_INSPECTING', progress: 94, step: '답변검사' }, { status: 'COMPLETED', progress: 100, step: '완료' },
]
const jobs = new Map<string, AnalysisJob>()
const positions = new Map<string, number>()
const now = () => new Date().toISOString()
const isTerminal = (status: JobStatus) => ['COMPLETED', 'BLOCKED', 'FAILED', 'CANCELLED'].includes(status)

function clone(job: AnalysisJob): AnalysisJob { return { ...job, file: { ...job.file } } }
function jobFromState(jobId: string, input: CreateJobInput, position = 0): AnalysisJob { const state = progressStates[position] ?? progressStates[0]; const timestamp = now(); return { jobId, requestId: `REQ-${crypto.randomUUID().slice(0, 8).toUpperCase()}`, file: input.file, status: state.status, currentStep: state.step, progress: state.progress, createdAt: timestamp, updatedAt: timestamp, canCancel: !isTerminal(state.status) } }

export async function mockCreateJob(input: CreateJobInput): Promise<AnalysisJob> { const jobId = `MOCK-JOB-${crypto.randomUUID().slice(0, 8).toUpperCase()}`; const job = jobFromState(jobId, input); jobs.set(jobId, job); positions.set(jobId, 0); return clone(job) }

function specialJob(jobId: string): AnalysisJob | null {
  const timestamp = now(); const file = { fileName: 'example.pdf', extension: 'PDF', size: 0 }
  if (jobId === 'mock-blocked') return { jobId, requestId: 'mock-c', file, status: 'BLOCKED', currentStep: '탐지', progress: 45, createdAt: timestamp, updatedAt: timestamp, canCancel: false }
  if (jobId === 'mock-failed') return { jobId, file, status: 'FAILED', currentStep: '파싱', progress: 30, createdAt: timestamp, updatedAt: timestamp, canCancel: false, failureMessage: '분석 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.' }
  if (jobId === 'mock-cancelled') return { jobId, file, status: 'CANCELLED', currentStep: '검사', progress: 16, createdAt: timestamp, updatedAt: timestamp, canCancel: false }
  return null
}

export async function mockGetJob(jobId: string): Promise<AnalysisJob> {
  if (jobId === 'mock-network-error') throw new Error('NETWORK_ERROR')
  let job = jobs.get(jobId)
  const special = specialJob(jobId); if (!job && special) return special
  if (!job && jobId.startsWith('MOCK-JOB-')) { job = jobFromState(jobId, { file: { fileName: '복구된 분석 요청', extension: '-', size: 0 } }); jobs.set(jobId, job); positions.set(jobId, 0) }
  if (!job) { const error = new Error('NOT_FOUND'); throw error }
  const position = positions.get(jobId) ?? 0
  if (!isTerminal(job.status)) { const nextPosition = Math.min(position + 1, progressStates.length - 1); const next = progressStates[nextPosition]; job = { ...job, status: next.status, currentStep: next.step, progress: next.progress, updatedAt: now(), canCancel: !isTerminal(next.status) }; jobs.set(jobId, job); positions.set(jobId, nextPosition) }
  return clone(job)
}

export async function mockCancelJob(jobId: string): Promise<AnalysisJob> { const current = await mockGetJob(jobId); const cancelled = { ...current, status: 'CANCELLED' as const, updatedAt: now(), canCancel: false }; jobs.set(jobId, cancelled); return clone(cancelled) }
export async function mockRetryJob(jobId: string): Promise<AnalysisJob> { const current = await mockGetJob(jobId); const retry = jobFromState(jobId, { file: current.file }); jobs.set(jobId, retry); positions.set(jobId, 0); return clone(retry) }
// 분석 Job의 상태 변화와 취소/재시도를 브라우저 안에서 흉내 내는 가짜 구현입니다.
