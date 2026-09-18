// 열 정의(columns)와 행 데이터(rows)를 받아 재사용 가능한 표를 그립니다.
import type { ReactNode } from 'react'
import { EmptyState, ErrorState, LoadingState } from './StateViews'
export interface DataTableColumn<T> { key: string; header: string; render: (row: T) => ReactNode }
export function DataTable<T extends { id: string }>({ columns, rows, loading, error, emptyMessage = '조회할 데이터가 없습니다.' }: { columns: DataTableColumn<T>[]; rows: T[]; loading?: boolean; error?: string; emptyMessage?: string }) { if (loading) return <LoadingState />; if (error) return <ErrorState label={error} />; if (rows.length === 0) return <EmptyState label={emptyMessage} />; return <div className="table-scroll"><table className="data-table"><thead><tr>{columns.map((column) => <th key={column.key}>{column.header}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key} data-label={column.header}>{column.render(row)}</td>)}</tr>)}</tbody></table></div> }
