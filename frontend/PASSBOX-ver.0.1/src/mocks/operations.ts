import type { OperationsDashboard } from '../types/operations'
import type { UserRole } from '../types/auth'

const timestamp = () => new Date().toISOString()
const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString()

function dashboardFor(scenario: string): OperationsDashboard {
  const busy = scenario === 'mock-busy'
  const degraded = scenario === 'mock-degraded'
  const down = scenario === 'mock-down'
  const incident = scenario === 'mock-incident'
  const queueScale = busy ? 4 : 1
  const hasIncident = incident || down

  return {
    generatedAt: timestamp(),
    summary: {
      totalRequests: busy ? 1842 : 1248,
      completedRequests: busy ? 1530 : 1130,
      blockedRequests: busy ? 101 : 67,
      failedRequests: down ? 74 : degraded ? 28 : 11,
      processingRequests: busy ? 137 : 40,
      successRate: down ? 91.2 : degraded ? 97.8 : 99.1,
      failureRate: down ? 4.0 : degraded ? 1.5 : 0.9,
    },
    queue: {
      totalQueued: 22 * queueScale,
      received: 3 * queueScale,
      inspecting: 4 * queueScale,
      parsing: 2 * queueScale,
      detecting: 5 * queueScale,
      masking: 2 * queueScale,
      waitingApproval: 3 * queueScale,
      transmitting: 1 * queueScale,
      postInspecting: 2 * queueScale,
    },
    performance: {
      averageProcessingTimeMs: down ? 4_820 : degraded ? 2_340 : busy ? 1_960 : 1_240,
      p95ProcessingTimeMs: down ? 11_200 : degraded ? 5_600 : busy ? 4_300 : 2_480,
      throughputPerHour: busy ? 286 : down ? 81 : 142,
    },
    providers: [
      { providerId: 'mock-secure-ai', providerName: 'Secure AI Gateway', status: down ? 'DOWN' : 'HEALTHY', responseTimeMs: down ? undefined : 186, lastCheckedAt: minutesAgo(1), message: down ? '연결 상태를 확인할 수 없습니다.' : '정상 응답 중입니다.' },
      { providerId: 'mock-inspector', providerName: 'Post-Inspector', status: degraded ? 'DEGRADED' : 'HEALTHY', responseTimeMs: degraded ? 1_420 : 242, lastCheckedAt: minutesAgo(1), message: degraded ? '응답 시간이 기준보다 높습니다.' : '정상 응답 중입니다.' },
      { providerId: 'mock-policy', providerName: 'Policy Service', status: 'HEALTHY', responseTimeMs: 94, lastCheckedAt: minutesAgo(2), message: '정상 응답 중입니다.' },
    ],
    recentJobs: [
      { jobId: 'JOB-OPS-001', requestId: 'REQ-OPS-001', fileNameDisplay: 'security_test_001.pdf', status: 'DETECTING', currentStep: '탐지', grade: 'S', startedAt: minutesAgo(4), updatedAt: minutesAgo(1), processingTimeMs: 182_000 },
      { jobId: 'JOB-OPS-002', requestId: 'REQ-OPS-002', fileNameDisplay: 'mock_report_002.pptx', status: 'COMPLETED', currentStep: '완료', grade: 'O', startedAt: minutesAgo(11), updatedAt: minutesAgo(8), processingTimeMs: 121_000 },
      { jobId: 'JOB-OPS-003', requestId: 'REQ-OPS-003', fileNameDisplay: 'sample_policy_003.xlsx', status: 'BLOCKED', currentStep: '탐지', grade: 'C', startedAt: minutesAgo(17), updatedAt: minutesAgo(15), processingTimeMs: 93_000 },
      { jobId: 'JOB-OPS-004', requestId: 'REQ-OPS-004', fileNameDisplay: 'test_document_004.pdf', status: 'WAITING_APPROVAL', currentStep: '승인대기', grade: 'S', startedAt: minutesAgo(26), updatedAt: minutesAgo(20), processingTimeMs: 318_000 },
    ],
    csoDistribution: [{ grade: 'C', count: busy ? 130 : 67 }, { grade: 'S', count: busy ? 309 : 221 }, { grade: 'O', count: busy ? 1403 : 960 }],
    incidents: hasIncident
      ? [{ incidentId: down ? 'INC-OPS-PROVIDER-001' : 'INC-OPS-QUEUE-001', severity: down ? 'HIGH' : 'MEDIUM', status: down ? 'OPEN' : 'INVESTIGATING', occurredAt: minutesAgo(8), summary: down ? 'Secure AI Gateway 상태를 확인할 수 없습니다.' : '분석 대기열이 기준치보다 높습니다.', relatedJobId: down ? 'JOB-OPS-001' : undefined }]
      : [],
  }
}

export async function mockGetOperationsDashboard(scenario: string, role: UserRole): Promise<OperationsDashboard> {
  if (role !== 'ADMIN' || scenario === 'mock-forbidden') throw new Error('FORBIDDEN')
  if (scenario === 'mock-network-error') throw new Error('NETWORK_ERROR')
  if (!['mock-normal', 'mock-busy', 'mock-degraded', 'mock-down', 'mock-incident'].includes(scenario)) throw new Error('NOT_FOUND')
  return structuredClone(dashboardFor(scenario))
}
// 운영 대시보드가 사용할 역할별 예시 지표와 알림 데이터입니다.
