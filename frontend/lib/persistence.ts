import type { Message } from '@/types'
import type { SessionData } from '@/app/page'

export function loadStorageItem<T>(
  key: string,
  validator: (value: unknown) => value is T
): T | null {
  const stored = window.localStorage.getItem(key)
  if (!stored) return null

  try {
    const parsed: unknown = JSON.parse(stored)
    return validator(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function saveStorageItem<T>(key: string, value: T) {
  window.localStorage.setItem(key, JSON.stringify(value))
}

export function removeStorageItem(key: string) {
  window.localStorage.removeItem(key)
}

export function isSessionData(value: unknown): value is SessionData {
  if (!value || typeof value !== 'object') return false

  const session = value as Record<string, unknown>

  return (
    typeof session.sessionId === 'string' &&
    Array.isArray(session.tables) &&
    session.tables.every(table => typeof table === 'string') &&
    typeof session.schema === 'string' &&
    typeof session.uploadedAt === 'string'
  )
}

export function isMessage(value: unknown): value is Message {
  if (!value || typeof value !== 'object') return false

  const message = value as Record<string, unknown>

  const hasValidRole = message.role === 'user' || message.role === 'assistant'
  const hasValidContent = typeof message.content === 'string'
  const hasValidPlan = message.plan === undefined || typeof message.plan === 'string'
  const hasValidSql = message.sql === undefined || typeof message.sql === 'string'
  const hasValidColumns =
    message.columns === undefined ||
    (Array.isArray(message.columns) &&
      message.columns.every(column => typeof column === 'string'))
  const hasValidRows =
    message.rows === undefined ||
    (Array.isArray(message.rows) &&
      message.rows.every(
        row =>
          Array.isArray(row) &&
          row.every(
            cell =>
              cell === null ||
              typeof cell === 'string' ||
              typeof cell === 'number' ||
              typeof cell === 'boolean'
          )
      ))
  const hasValidRowCount =
    message.row_count === undefined || typeof message.row_count === 'number'
  const hasValidError =
    message.error === undefined || typeof message.error === 'string'

  return (
    hasValidRole &&
    hasValidContent &&
    hasValidPlan &&
    hasValidSql &&
    hasValidColumns &&
    hasValidRows &&
    hasValidRowCount &&
    hasValidError
  )
}

export function isMessageList(value: unknown): value is Message[] {
  return Array.isArray(value) && value.every(isMessage)
}
