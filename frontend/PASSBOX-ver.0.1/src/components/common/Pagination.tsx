// 목록이 일정 개수를 넘으면 한 화면에 전부 뿌리는 대신 페이지로 나눠 보여 줍니다.
import { Button } from './Button'

export function Pagination({ page, pageCount, pageSize, totalCount, onPageChange }: { page: number; pageCount: number; pageSize: number; totalCount: number; onPageChange: (page: number) => void }) {
  if (pageCount <= 1) return null
  const start = totalCount === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, totalCount)
  return (
    <nav className="pagination" aria-label="페이지 탐색">
      <p className="pagination__summary">전체 {totalCount}건 중 {start}–{end}건</p>
      <div className="pagination__controls">
        <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>이전</Button>
        <ul className="pagination__pages">
          {Array.from({ length: pageCount }, (_, index) => index + 1).map((pageNumber) => (
            <li key={pageNumber}>
              <button
                type="button"
                className={`pagination__page ${pageNumber === page ? 'pagination__page--active' : ''}`.trim()}
                aria-current={pageNumber === page ? 'page' : undefined}
                onClick={() => onPageChange(pageNumber)}
              >
                {pageNumber}
              </button>
            </li>
          ))}
        </ul>
        <Button size="sm" variant="ghost" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>다음</Button>
      </div>
    </nav>
  )
}
