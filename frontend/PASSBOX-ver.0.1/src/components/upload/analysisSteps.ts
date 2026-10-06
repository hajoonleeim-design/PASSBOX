// 문서 분석 Job(job_worker.process_document_job)이 실제로 거치는 단계만 나열한다.
// 마스킹/승인대기/전송/답변검사는 분류 확정 뒤 "Gateway 전송 테스트"를 따로 눌렀을 때만
// 발생하는 별도 흐름(OutboundApproval)이라 이 Job의 단계 표시기에는 해당하지 않는다.
export const analysisSteps = ['접수', '검사', '파싱', '탐지', '분류 검토', '완료'] as const
