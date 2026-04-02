import { Badge } from '@/components/ui/badge'
import type { TableCell } from '@/types'

interface Props {
  columns: string[]
  rows: TableCell[][]
  row_count: number
}

export default function ResultTable({ columns, rows, row_count }: Props) {
  return (
    <div className="space-y-2 w-full">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="text-xs">
          {row_count} row{row_count !== 1 ? 's' : ''}
        </Badge>
      </div>
      <div className="w-full overflow-x-auto overflow-y-auto max-h-72 rounded-xl border">
        <table className="min-w-full text-sm border-collapse">
          <thead className="sticky top-0 z-10 bg-muted">
            <tr>
              {columns.map(col => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-left text-muted-foreground font-medium whitespace-nowrap border-b"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b last:border-0 hover:bg-muted/30 transition-colors"
              >
                {row.map((cell, j) => (
                  <td
                    key={j}
                    className="px-4 py-2 text-foreground whitespace-nowrap font-mono"
                  >
                    {typeof cell === 'number'
                      ? Math.round(cell * 100) / 100
                      : cell ?? '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
