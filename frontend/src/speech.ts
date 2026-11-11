import { useCallback, useEffect, useRef, useState } from 'react'

// Browser Web Speech API type declarations
interface IWindow extends Window {
  SpeechRecognition?: any
  webkitSpeechRecognition?: any
}

export function isSpeechRecognitionSupported(): boolean {
  if (typeof window === 'undefined') return false
  const w = window as IWindow
  return !!(w.SpeechRecognition || w.webkitSpeechRecognition)
}

export function useSpeechRecognition() {
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)
  const isSupported = isSpeechRecognitionSupported()

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore already stopped
      }
    }
    setIsListening(false)
  }, [])

  const startListening = useCallback(() => {
    setError(null)
    setTranscript('')
    setInterimTranscript('')

    if (!isSupported) {
      setError('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.')
      return
    }

    try {
      const w = window as IWindow
      const SpeechRecognitionClass = w.SpeechRecognition || w.webkitSpeechRecognition
      const rec = new SpeechRecognitionClass()
      rec.continuous = true
      rec.interimResults = true
      rec.lang = 'en-US'

      rec.onstart = () => {
        setIsListening(true)
      }

      rec.onresult = (event: any) => {
        let finalTxt = ''
        let interimTxt = ''
        for (let i = 0; i < event.results.length; i++) {
          const res = event.results[i]
          if (res.isFinal) {
            finalTxt += res[0].transcript + ' '
          } else {
            interimTxt += res[0].transcript + ' '
          }
        }
        if (finalTxt) {
          setTranscript(finalTxt.trim())
        }
        setInterimTranscript(interimTxt.trim())
      }

      rec.onerror = (e: any) => {
        if (e.error !== 'no-speech') {
          setError(e.error === 'not-allowed' ? 'Microphone permission denied.' : `Speech error: ${e.error}`)
        }
      }

      rec.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = rec
      rec.start()
    } catch (e: any) {
      setError(String(e.message ?? e))
      setIsListening(false)
    }
  }, [isSupported])

  const resetTranscript = useCallback(() => {
    setTranscript('')
    setInterimTranscript('')
    setError(null)
  }, [])

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch {
          // cleanup
        }
      }
    }
  }, [])

  return {
    transcript,
    interimTranscript,
    isListening,
    error,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
  }
}

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<any>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const startRecording = useCallback(async () => {
    setError(null)
    setAudioUrl(null)
    setDuration(0)
    chunksRef.current = []

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Audio recording is not supported in this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const url = URL.createObjectURL(blob)
        setAudioUrl(url)
        // Release tracks
        stream.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }

      recorder.start(100)
      setIsRecording(true)

      const startTs = Date.now()
      timerRef.current = setInterval(() => {
        setDuration(Math.round((Date.now() - startTs) / 100) / 10)
      }, 100)
    } catch (e: any) {
      setError(e.name === 'NotAllowedError' ? 'Microphone access denied.' : String(e.message ?? e))
      setIsRecording(false)
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop()
      } catch {
        // ignore
      }
    }
    setIsRecording(false)
  }, [])

  const resetAudio = useCallback(() => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
    setAudioUrl(null)
    setDuration(0)
    setError(null)
  }, [audioUrl])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }
    }
  }, [])

  return {
    isRecording,
    audioUrl,
    duration,
    error,
    startRecording,
    stopRecording,
    resetAudio,
  }
}

export type DiffWord = {
  text: string
  status: 'matched' | 'missed' | 'extra'
}

export function diffWords(target: string, spoken: string): { diff: DiffWord[]; accuracy: number } {
  const clean = (s: string) => s.toLowerCase().replace(/[^a-z0-9'\s]/g, '').trim()
  const targetWords = target.trim().split(/\s+/).filter(Boolean)
  const spokenWords = clean(spoken).split(/\s+/).filter(Boolean)

  if (!targetWords.length) {
    return { diff: [], accuracy: 100 }
  }

  let matchedCount = 0
  let sIdx = 0
  const diff: DiffWord[] = []

  for (let i = 0; i < targetWords.length; i++) {
    const rawTarget = targetWords[i]
    const cleanTarget = clean(rawTarget)

    // Look ahead within spoken words window
    let foundIdx = -1
    for (let j = sIdx; j < Math.min(sIdx + 4, spokenWords.length); j++) {
      if (spokenWords[j] === cleanTarget) {
        foundIdx = j
        break
      }
    }

    if (foundIdx !== -1) {
      // Mark any intervening spoken words as extra
      while (sIdx < foundIdx) {
        diff.push({ text: spokenWords[sIdx], status: 'extra' })
        sIdx++
      }
      diff.push({ text: rawTarget, status: 'matched' })
      matchedCount++
      sIdx++
    } else {
      diff.push({ text: rawTarget, status: 'missed' })
    }
  }

  // Any remaining spoken words
  while (sIdx < spokenWords.length) {
    diff.push({ text: spokenWords[sIdx], status: 'extra' })
    sIdx++
  }

  const accuracy = Math.round((matchedCount / targetWords.length) * 100)
  return { diff, accuracy }
}
