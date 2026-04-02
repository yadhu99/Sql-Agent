export type TableCell = string | number | boolean | null

export interface UploadResponse {
  session_id: string
  tables: string[]
  schema: string
  message: string
}

export interface ChatResponse {
  success: boolean
  question: string
  sql: string
  columns: string[]
  rows: TableCell[][]
  row_count: number
  error?: string
}

export interface Message {
  role: 'user' | 'assistant'
  plan?: string
  content: string
  sql?: string
  columns?: string[]
  rows?: TableCell[][]
  row_count?: number
  error?: string
}
