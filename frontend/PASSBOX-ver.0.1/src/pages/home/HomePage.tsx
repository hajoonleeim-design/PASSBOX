// 서비스 진입 화면으로, 주요 기능으로 이동하는 버튼을 제공합니다.
import { useNavigate } from 'react-router-dom'
import { Alert } from '../../components/common/Alert'
import { Button } from '../../components/common/Button'
import { Card } from '../../components/common/Card'
import { DataTable, type DataTableColumn } from '../../components/common/DataTable'
import { StatusBadge } from '../../components/common/StatusBadge'
import { useAuth } from '../../hooks/useAuth'

interface RecentWork { id: string; request: string; status: '완료' | '검사' | '승인대기'; updatedAt: string }
const recentWork: RecentWork[] = [{ id: 'sample-1', request: '예시 요청', status: '완료', updatedAt: 'Mock 데이터' }, { id: 'sample-2', request: '예시 문서 분석', status: '검사', updatedAt: 'Mock 데이터' }]
const columns: DataTableColumn<RecentWork>[] = [{ key: 'request', header: '작업', render: (item) => item.request }, { key: 'status', header: '상태', render: (item) => <StatusBadge label={item.status} /> }, { key: 'updatedAt', header: '최근 업데이트', render: (item) => item.updatedAt }]

export function HomePage() { const { session } = useAuth(); const navigate = useNavigate(); return <section><p className="eyebrow">SERVICE HOME</p><h1>{session?.displayName}님, 안전한 AI 업무를 시작하세요.</h1><p>{session?.institutionName} · {session?.role} 권한으로 접속 중입니다.</p><div className="action-grid"><Card><p className="eyebrow">PROMPT</p><h2>일상 AI 대화</h2><p>문서 없이 업무 질문을 입력합니다. 전송 전 보안 정책 검사가 적용됩니다.</p><Button onClick={() => navigate('/chat')}>일상 대화 시작</Button></Card><Card><p className="eyebrow">DOCUMENT</p><h2>문서 업로드</h2><p>문서를 업로드하여 서버 검증과 보안 분석을 요청합니다.</p><Button onClick={() => navigate('/upload')}>문서 업로드</Button></Card></div><div className="dashboard-grid"><Card><div className="section-heading"><div><h2>최근 작업</h2><p>현재 화면은 개발용 Mock 상태를 표시합니다.</p></div></div><DataTable columns={columns} rows={recentWork} emptyMessage="최근 분석 작업이 없습니다." /></Card><div className="stack"><Card><h2>현재 접속 정보</h2><dl className="info-list"><div><dt>기관</dt><dd>{session?.institutionName}</dd></div><div><dt>역할</dt><dd>{session?.role}</dd></div><div><dt>세션</dt><dd>정상</dd></div></dl></Card><Alert variant="info" title="정책 안내">민감한 정보는 입력 또는 업로드 전 기관의 보안 정책을 확인해 주세요.</Alert></div></div></section> }
