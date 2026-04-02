'use client'

import { useState, useRef, useEffect, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import axios from 'axios'
import { Message, ChatResponse } from '@/types'
import { isMessageList, loadStorageItem, removeStorageItem, saveStorageItem } from '@/lib/persistence'
import ResultTable from './ResultTable'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Send, Loader2, Bot } from 'lucide-react'

interface Props {
  sessionId: string
}

export default function Chat({ sessionId }: Props) {
  const { data: session } = useSession()
  const [messagesState, setMessagesState] = useState<{
    key: string | null
    value: Message[] | undefined
  }>({ key: null, value: undefined })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const storageKey = useMemo(() => {
    if (!session?.user?.id || !sessionId) return null
    return `sql-agent:messages:${session.user.id}:${sessionId}`
  }, [session?.user?.id, sessionId])
  const restoredMessages = useMemo(() => {
    if (!storageKey) return []

    const restored = loadStorageItem(storageKey, isMessageList)
    if (!restored) {
      removeStorageItem(storageKey)
      return []
    }

    return restored
  }, [storageKey])
  const messages =
    messagesState.key === storageKey && messagesState.value !== undefined
      ? messagesState.value
      : restoredMessages

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const commitMessages = (updater: Message[] | ((prev: Message[]) => Message[])) => {
    const nextMessages = typeof updater === 'function' ? updater(messages) : updater

    if (storageKey) {
      saveStorageItem(storageKey, nextMessages)
    }

    setMessagesState({ key: storageKey, value: nextMessages })
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    commitMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await axios.post<ChatResponse>(
        'http://localhost:8000/api/chat/',
        { session_id: sessionId, question: input },
        { headers: { 'Content-Type': 'application/json' } }
      )

      const data = response.data
      commitMessages(prev => [...prev, {
        role: 'assistant',
        content: data.success ? '' : data.error || 'Something went wrong',
        sql: data.sql,
        columns: data.columns,
        rows: data.rows,
        row_count: data.row_count,
      }])
    } catch (err: unknown) {
      commitMessages(prev => [...prev, {
        role: 'assistant',
        content: axios.isAxiosError(err)
          ? err.response?.data?.error || 'Something went wrong'
          : 'Something went wrong'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const suggestions = [
    'Show total sales per customer',
    'Which products have the highest rating?',
    'Show revenue by category',
    'List all pending orders',
  ]

  return (
    <div className="flex h-full min-h-0 flex-col">

      <ScrollArea className="min-h-0 flex-1">
        <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">

          {messages.length === 0 && (
            <div className="space-y-8 pt-8">
              <div className="text-center space-y-2">
                <p className="text-lg font-semibold">What would you like to know?</p>
                <p className="text-sm text-muted-foreground">
                  Ask anything about your data in plain English
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s)}
                    className="text-left text-xs text-muted-foreground bg-muted/40 hover:bg-muted border rounded-xl px-4 py-3 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 bg-primary/10 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5 text-primary" />
                </div>
              )}

              <div className={`space-y-3 ${msg.role === 'user' ? 'max-w-md' : 'flex-1 min-w-0'}`}>
                {msg.role === 'user' ? (
                  <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 inline-block">
                    <p className="text-sm">{msg.content}</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {msg.sql && (
                      <div className="bg-muted/40 border rounded-xl p-4 space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">Generated SQL</p>
                        <code className="text-xs text-emerald-400 whitespace-pre-wrap break-all font-mono leading-relaxed">
                          {msg.sql}
                        </code>
                      </div>
                    )}
                    {msg.columns && msg.rows && (
                      <ResultTable
                        columns={msg.columns}
                        rows={msg.rows}
                        row_count={msg.row_count || 0}
                      />
                    )}
                    {msg.content && (
                      <p className="text-sm text-destructive">{msg.content}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-7 h-7 bg-primary/10 rounded-full flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
              <div className="bg-muted/40 border rounded-xl px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* input */}
      <div className="border-t bg-card/30 backdrop-blur-sm p-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data..."
            disabled={loading}
            className="flex-1"
          />
          <Button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            size="icon"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
