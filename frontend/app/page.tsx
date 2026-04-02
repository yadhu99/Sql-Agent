'use client'

import { useSession, signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useEffect, useMemo, useState } from 'react'
import Sidebar from '@/components/Sidebar'
import Chat from '@/components/Chat'
import Onboarding from '@/components/Onboarding'
import { isSessionData, loadStorageItem, removeStorageItem, saveStorageItem } from '@/lib/persistence'
import { Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

export interface SessionData {
  sessionId: string
  tables: string[]
  schema: string
  uploadedAt: string
}

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [csvSessionState, setCsvSessionState] = useState<{
    key: string | null
    value: SessionData | null | undefined
  }>({ key: null, value: undefined })
  const [showOnboarding, setShowOnboarding] = useState(false)
  const storageKey = useMemo(() => {
    if (!session?.user?.id) return null
    return `sql-agent:csv-session:${session.user.id}`
  }, [session?.user?.id])
  const restoredCsvSession = useMemo(() => {
    if (!storageKey) return null

    const restored = loadStorageItem(storageKey, isSessionData)
    if (!restored) {
      removeStorageItem(storageKey)
    }

    return restored
  }, [storageKey])
  const csvSession =
    csvSessionState.key === storageKey && csvSessionState.value !== undefined
      ? csvSessionState.value
      : restoredCsvSession

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin')
    }
  }, [status, router])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!session) return null

  const handleUploadSuccess = (sessionId: string, tables: string[], schema: string) => {
    const nextSession = {
      sessionId,
      tables,
      schema,
      uploadedAt: new Date().toLocaleString(),
    }

    if (storageKey) {
      saveStorageItem(storageKey, nextSession)
    }

    setCsvSessionState({ key: storageKey, value: nextSession })
    setShowOnboarding(false)
  }

  const handleNewChat = () => {
    if (storageKey) {
      removeStorageItem(storageKey)
    }

    setCsvSessionState({ key: storageKey, value: null })
    setShowOnboarding(true)
  }

  return (
    <main className="flex flex-col h-screen overflow-hidden">

      {/* navbar */}
      <nav className="h-14 border-b flex items-center justify-between px-6 shrink-0 bg-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Database className="w-4 h-4 text-primary-foreground" />
          </div>
          <div>
            <span className="text-sm font-semibold">SQL Agent</span>
            <span className="text-xs text-muted-foreground ml-2">AI-powered data queries</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            className="gap-2 text-xs"
          >
            <span>+</span> New chat
          </Button>

          {/* user avatar */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground hidden sm:block">
              {session.user?.name}
            </span>
            {session.user?.image && (
              <Image
                src={session.user.image}
                alt="avatar"
                width={28}
                height={28}
                className="w-7 h-7 rounded-full"
              />
            )}
          </div>
        </div>
      </nav>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar
          session={csvSession}
          onSignOut={() => signOut({ callbackUrl: '/auth/signin' })}
        />
        <Separator orientation="vertical" />

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {!csvSession && !showOnboarding && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4 max-w-sm">
                <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto">
                  <Database className="w-8 h-8 text-primary" />
                </div>
                <div className="space-y-1">
                  <p className="text-lg font-semibold">
                    Welcome, {session.user?.name?.split(' ')[0]}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Upload CSV files and query your data using plain English
                  </p>
                </div>
                <Button onClick={() => setShowOnboarding(true)} className="gap-2">
                  <span>+</span> Get started
                </Button>
              </div>
            </div>
          )}

          {showOnboarding && !csvSession && (
            <Onboarding onUploadSuccess={handleUploadSuccess} />
          )}

          {csvSession && (
            <Chat sessionId={csvSession.sessionId} />
          )}
        </div>
      </div>

      <div className="pointer-events-none fixed bottom-5 right-5 text-xs font-medium italic tracking-wide text-muted-foreground/55">
        Built by Yadhu
      </div>
    </main>
  )
}
