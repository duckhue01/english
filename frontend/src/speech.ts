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

function encodeWav(samples: Float32Array, sampleRate = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  // RIFF chunk descriptor
  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(8, 'WAVE')

  // fmt sub-chunk
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true) // 16 for PCM
  view.setUint16(20, 1, true) // PCM format = 1
  view.setUint16(22, 1, true) // mono = 1
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate = sampleRate * 1 * 2
  view.setUint16(32, 2, true) // block align = 2
  view.setUint16(34, 16, true) // bits per sample = 16

  // data sub-chunk
  writeString(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  // write 16-bit PCM samples
  let offset = 44
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }

  return new Blob([view], { type: 'audio/wav' })
}

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const audioContextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const samplesRef = useRef<Float32Array[]>([])
  const timerRef = useRef<any>(null)

  const startRecording = useCallback(async () => {
    setError(null)
    setAudioUrl(null)
    setAudioBlob(null)
    setDuration(0)
    samplesRef.current = []

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Audio recording is not supported in this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000 },
      })
      streamRef.current = stream

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      const audioCtx = new AudioCtx({ sampleRate: 16000 })
      audioContextRef.current = audioCtx

      const source = audioCtx.createMediaStreamSource(stream)
      sourceRef.current = source

      const processor = audioCtx.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0)
        samplesRef.current.push(new Float32Array(inputData))
      }

      source.connect(processor)
      processor.connect(audioCtx.destination)

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

    if (processorRef.current && sourceRef.current) {
      try {
        processorRef.current.disconnect()
        sourceRef.current.disconnect()
      } catch {
        // ignore
      }
    }

    if (audioContextRef.current) {
      try {
        audioContextRef.current.close()
      } catch {
        // ignore
      }
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }

    // Merge Float32Array chunks and encode as 16kHz WAV
    const chunks = samplesRef.current
    if (chunks.length > 0) {
      const totalLen = chunks.reduce((acc, c) => acc + c.length, 0)
      const merged = new Float32Array(totalLen)
      let offset = 0
      for (const c of chunks) {
        merged.set(c, offset)
        offset += c.length
      }

      const wavBlob = encodeWav(merged, 16000)
      setAudioBlob(wavBlob)
      const url = URL.createObjectURL(wavBlob)
      setAudioUrl(url)
    }

    setIsRecording(false)
  }, [])

  const resetAudio = useCallback(() => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
    }
    setAudioUrl(null)
    setAudioBlob(null)
    setDuration(0)
    setError(null)
  }, [audioUrl])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }
      if (audioContextRef.current) {
        try {
          audioContextRef.current.close()
        } catch {
          // cleanup
        }
      }
    }
  }, [])

  return {
    isRecording,
    audioUrl,
    audioBlob,
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
