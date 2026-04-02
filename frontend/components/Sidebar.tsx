'use client'

import { useState } from 'react'
import { SessionData } from '@/app/page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChevronRight, Table2, Clock, Hash, Settings, X, Sun, Moon, LogOut } from 'lucide-react'

interface Props {
  session: SessionData | null
  onSignOut: () => void
}

export default function Sidebar({ session, onSignOut }: Props) {
  const [schemaOpen, setSchemaOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  const toggleTheme = (selected: 'light' | 'dark') => {
    setTheme(selected)
    document.documentElement.classList.toggle('dark', selected === 'dark')
  }

  return (
    <div className="w-64 bg-muted/40 border-r flex flex-col overflow-hidden shrink-0 relative">

      <div className="px-4 py-3 border-b">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Session
        </p>
      </div>

      {!session ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-xs text-muted-foreground text-center">
            No active session.<br />Upload CSVs to get started.
          </p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="p-3 space-y-5">

            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Hash className="w-3 h-3" />
                <span>Session ID</span>
              </div>
              <div className="bg-muted/50 rounded-md px-2.5 py-1.5 border">
                <p className="text-xs font-mono text-foreground truncate">{session.sessionId}</p>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                <span>Uploaded at</span>
              </div>
              <p className="text-xs text-foreground">{session.uploadedAt}</p>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Table2 className="w-3 h-3" />
                  <span>Tables</span>
                </div>
                <Badge variant="secondary" className="text-xs px-1.5 py-0">
                  {session.tables.length}
                </Badge>
              </div>
              <div className="space-y-1">
                {session.tables.map(table => (
                  <div
                    key={table}
                    className="flex items-center gap-2 rounded-md px-2.5 py-1.5 hover:bg-muted/50 transition-colors"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                    <span className="text-xs font-mono text-foreground truncate">{table}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <button
                onClick={() => setSchemaOpen(!schemaOpen)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
              >
                <ChevronRight className={`w-3 h-3 transition-transform ${schemaOpen ? 'rotate-90' : ''}`} />
                <span>Schema</span>
              </button>
              {schemaOpen && (
                <pre className="text-xs text-muted-foreground whitespace-pre-wrap bg-muted/30 border rounded-md p-2.5 overflow-auto max-h-80 leading-relaxed font-mono">
                  {session.schema}
                </pre>
              )}
            </div>

          </div>
        </ScrollArea>
      )}

      {/* settings button */}
      <div className="border-t p-3">
        <button
          onClick={() => setSettingsOpen(true)}
          className="flex items-center gap-2.5 w-full rounded-md px-2.5 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
      </div>

      {/* settings panel — slides in over the sidebar */}
      {settingsOpen && (
        <div className="absolute inset-0 bg-background border-r flex flex-col z-10">

          {/* header */}
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <p className="text-sm font-medium">Settings</p>
            <button
              onClick={() => setSettingsOpen(false)}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* content */}
          <div className="p-4 space-y-6">

            {/* theme */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Appearance
              </p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => toggleTheme('light')}
                  className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition-all
                    ${theme === 'light'
                      ? 'border-foreground bg-muted'
                      : 'border-border hover:border-muted-foreground'
                    }`}
                >
                  <Sun className="w-5 h-5" />
                  <span className="text-xs font-medium">Light</span>
                </button>
                <button
                  onClick={() => toggleTheme('dark')}
                  className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition-all
                    ${theme === 'dark'
                      ? 'border-foreground bg-muted'
                      : 'border-border hover:border-muted-foreground'
                    }`}
                >
                  <Moon className="w-5 h-5" />
                  <span className="text-xs font-medium">Dark</span>
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Account
              </p>
              <Button
                variant="outline"
                onClick={onSignOut}
                className="w-full justify-start gap-2"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </Button>
            </div>

          </div>
        </div>
      )}

    </div>
  )
}
