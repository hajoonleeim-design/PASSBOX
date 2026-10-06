// 목록이 일정 개수를 넘으면 현재 페이지에 해당하는 구간만 잘라서 돌려줍니다.
export function paginate<T>(items: T[], page: number, pageSize: number): { pageItems: T[]; pageCount: number; safePage: number } {
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize))
  const safePage = Math.min(Math.max(1, page), pageCount)
  const start = (safePage - 1) * pageSize
  return { pageItems: items.slice(start, start + pageSize), pageCount, safePage }
}
