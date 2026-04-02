'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Upload, FileText, X, Loader2 } from 'lucide-react'

interface Props {
  onUploadSuccess: (sessionId: string, tables: string[], schema: string) => void
}

export default function Onboarding({ onUploadSuccess }: Props) {
  const [sessionId, setSessionId] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles])
    setError('')
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    multiple: true,
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (!sessionId.trim()) { setError('Please enter a session ID'); return }
    if (files.length === 0) { setError('Please upload at least one CSV file'); return }

    setLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('session_id', sessionId)
      files.forEach(file => formData.append('files', file))

      const response = await axios.post(
        'http://localhost:8000/api/upload/csv/',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )

      onUploadSuccess(sessionId, response.data.tables, response.data.schema)
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? err.response?.data?.error || 'Upload failed'
          : 'Upload failed'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
      <div className="w-full max-w-lg space-y-6">

        {/* header */}
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">New chat</h2>
          <p className="text-sm text-muted-foreground">
            Upload your CSV files to start querying with AI
          </p>
        </div>

        {/* session id */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Session ID</label>
          <Input
            value={sessionId}
            onChange={e => setSessionId(e.target.value)}
            placeholder="e.g. sales-analysis-01"
          />
          <p className="text-xs text-muted-foreground">
            Use the same session ID to continue a previous chat
          </p>
        </div>

        {/* dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all
            ${isDragActive
              ? 'border-primary bg-primary/5 scale-[1.01]'
              : 'border-border hover:border-primary/50 hover:bg-muted/30'
            }`}
        >
          <input {...getInputProps()} />
          <div className="space-y-3">
            <div className="w-12 h-12 bg-muted rounded-xl flex items-center justify-center mx-auto">
              <Upload className="w-5 h-5 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                {isDragActive ? 'Drop your files here' : 'Drag & drop CSV files'}
              </p>
              <p className="text-xs text-muted-foreground">
                or click to browse — supports multiple files
              </p>
            </div>
          </div>
        </div>

        {/* file list */}
        {files.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground font-medium">
              {files.length} file{files.length > 1 ? 's' : ''} selected
            </p>
            <div className="space-y-1.5">
              {files.map((file, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between bg-muted/40 border rounded-lg px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span className="text-xs font-mono text-foreground">{file.name}</span>
                  </div>
                  <button
                    onClick={() => removeFile(i)}
                    className="text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* error */}
        {error && (
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
            <p className="text-destructive text-xs">{error}</p>
          </div>
        )}

        {/* submit */}
        <Button
          onClick={handleUpload}
          disabled={loading}
          className="w-full"
          size="lg"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Analyzing your data...
            </>
          ) : (
            'Upload & Start Chat'
          )}
        </Button>

      </div>
    </div>
  )
}
