export type LinkInfo = {
  type: 'cv' | 'glide_j' | 'glide_w' | 'vv' | 'same' | 'held_stop' | 'coalesce'
  label: string
  insert: string | null
}

export type Syllable = { ipa: string; stress: number; features: string[] }

export type WordToken = {
  is_word: true
  text: string
  source: 'cmu' | 'g2p' | 'unknown'
  weak: boolean
  syllables: Syllable[]
  ipa: string
  spelling: string[] | null
  stressed_spelling: number | null
  link_next: LinkInfo | null
}
export type PunctToken = { is_word: false; text: string }
export type Token = WordToken | PunctToken

export type Status = 'new' | 'practicing' | 'fixed'
export type Kind = 'vocab' | 'mistake'

export type Item = {
  id: string
  note_id: string
  note_title?: string
  folder: string
  kind: Kind
  text: string
  context: string
  ctx_start: number
  ctx_end: number
  position: number
  status: Status
  comment: string
  updated_at: string
  analysis?: Token[]
}

export type Folder = {
  name: string
  added_at: string
  last_synced: string | null
  last_source: string | null
  notes: number
  vocab: number
  mistakes: number
}

export type AppleFolder = { name: string; account: string; note_count: number }

export type Run = {
  start: number
  end: number
  bold: boolean
  italic: boolean
  underline: boolean
  strike: boolean
  highlight: number
  heading: number
  link: string | null
}

export type NoteSummary = {
  id: string
  folder: string
  title: string
  modified: string
  vocab: number
  mistakes: number
}

export type NoteDetail = NoteSummary & { text: string; runs: Run[]; items: Item[] }

export type AppStatus = {
  reader: 'notestore' | 'applescript'
  full_disk_access: boolean
  highlight_supported: boolean
}

export type SyncReport = {
  source: string
  folders: { folder: string; notes: number; vocab: number; mistake: number; new_items: number }[]
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let msg = res.statusText
    try {
      msg = (await res.json()).detail ?? msg
    } catch {
      /* ignore */
    }
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

const qs = (p: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams()
  Object.entries(p).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      s.set(k, String(v))
    }
  })
  const str = s.toString()
  return str ? `?${str}` : ''
}

export type QAKeyPoint = {
  title: string
  description: string
  status?: 'covered' | 'partial' | 'missing'
  matched_terms?: string[]
}

export type QAItem = {
  id: string
  folder: string
  note_id: string
  note_title: string
  topic: string
  subtopic: string
  question: string
  key_points: QAKeyPoint[]
}

export type QAEvalResult = {
  coverage_pct: number
  covered_count: number
  total_points: number
  key_points: QAKeyPoint[]
  word_count: number
  duration_sec: number
  wpm: number
  pace_feedback: string
  summary: string
  spoken_text: string
}

export type ShadowingSentence = {
  id: string
  text: string
  target_word: string
  kind: string
  folder: string
  note_id: string
  note_title: string
  tokens: Token[]
}

export type G2PPhoneme = {
  arpabet: string
  base: string
  stress: number | null
  ipa: string
  is_vowel: boolean
  tip?: string
}

export type G2PWord = {
  word: string
  arpabet: string[]
  ipa: string
  phonemes: G2PPhoneme[]
}

export type WhisperWord = {
  target: string
  spoken: string
  status: 'correct' | 'substituted' | 'omitted' | 'inserted'
}

export type SimplePronScore = {
  method: 'whisper'
  accuracy_score: number
  word_error_rate: number
  recognized_text: string
  target_text: string
  words: WhisperWord[]
}

export type GOPPhoneme = {
  arpabet: string
  ipa: string
  stress: number | null
  gop_score: number
  is_mispronounced: boolean
  start_time: number
  end_time: number
  tip?: string
}

export type GOPWord = {
  word: string
  ipa: string
  score: number
  is_mispronounced: boolean
  start_time: number
  end_time: number
  phonemes: GOPPhoneme[]
}

export type AdvancedPronScore = {
  method: 'wav2vec2_gop'
  overall_score: number
  threshold: number
  words: GOPWord[]
  target_text: string
  error?: string
}

export type PronEvaluationResult = {
  simple: SimplePronScore
  advanced: AdvancedPronScore
  overall_score: number
}

export const api = {
  status: () => req<AppStatus>('/status'),
  appleFolders: () => req<AppleFolder[]>('/apple-folders'),
  folders: () => req<Folder[]>('/folders'),
  addFolder: (name: string) => req('/folders', { method: 'POST', body: JSON.stringify({ name }) }),
  removeFolder: (name: string) =>
    req(`/folders/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  sync: (folders?: string[]) =>
    req<SyncReport>('/sync', { method: 'POST', body: JSON.stringify({ folders: folders ?? null }) }),
  items: (p: { kind?: Kind; status?: string; folder?: string; q?: string; note_id?: string }) =>
    req<Item[]>(`/items${qs(p)}`),
  updateItem: (id: string, patch: { status?: Status; comment?: string }) =>
    req<Item>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  notes: (folder?: string) => req<NoteSummary[]>(`/notes${qs({ folder })}`),
  note: (id: string) => req<NoteDetail>(`/notes/${encodeURIComponent(id)}`),
  analyze: (text: string) =>
    req<Token[]>('/analyze', { method: 'POST', body: JSON.stringify({ text }) }),
  analyzeBatch: (texts: string[]) =>
    req<Token[][]>('/analyze-batch', { method: 'POST', body: JSON.stringify({ texts }) }),
  speakingQA: (folder?: string) => req<QAItem[]>(`/speaking/qa${qs({ folder })}`),
  speakingSentences: (p: { folder?: string; note_id?: string; limit?: number }) =>
    req<ShadowingSentence[]>(`/speaking/sentences${qs(p)}`),
  evaluateAnswer: (body: { question: QAItem; spoken_text: string; duration_sec: number }) =>
    req<QAEvalResult>('/speaking/evaluate-answer', { method: 'POST', body: JSON.stringify(body) }),
  g2p: (text: string) => req<G2PWord[]>('/pron/g2p', { method: 'POST', body: JSON.stringify({ text }) }),
  scoreAudio: async (
    audioBlob: Blob,
    targetText: string,
    method: 'simple' | 'advanced' | 'both' = 'both',
    threshold = 0.5,
  ): Promise<PronEvaluationResult> => {
    const formData = new FormData()
    formData.append('file', audioBlob, 'recording.wav')
    formData.append('target_text', targetText)
    formData.append('method', method)
    formData.append('threshold', String(threshold))

    const res = await fetch('/api/pron/score', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      let msg = res.statusText
      try {
        msg = (await res.json()).detail ?? msg
      } catch {
        /* ignore */
      }
      throw new Error(msg)
    }
    return res.json()
  },
}

let currentTTSAudio: HTMLAudioElement | null = null
let cachedBrowserVoices: SpeechSynthesisVoice[] = []

if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    cachedBrowserVoices = window.speechSynthesis.getVoices()
  }
}

function getBestBrowserVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null
  if (!cachedBrowserVoices.length) {
    cachedBrowserVoices = window.speechSynthesis.getVoices()
  }
  const roboticVoices = /Alex|Fred|Zarvox|Cellos|Bells|Boing|Bad News|Good News|Trinoids|Whisper/i
  const enVoices = cachedBrowserVoices.filter(
    (v) => v.lang.replace('_', '-').startsWith('en') && !roboticVoices.test(v.name)
  )

  // 1. Premium / Enhanced / Natural
  const premium = enVoices.find((v) => /enhanced|premium|natural|online/i.test(v.name))
  if (premium) return premium

  // 2. High quality Google US / Samantha / Ava / Jenny / Siri
  const preferred = enVoices.find((v) =>
    /Google US|Samantha|Ava|Jenny|Aria|Siri|Allison/i.test(v.name)
  )
  if (preferred) return preferred

  // 3. Any standard en-US voice
  const usVoice = enVoices.find((v) => v.lang.replace('_', '-').startsWith('en-US'))
  if (usVoice) return usVoice

  return enVoices[0] || null
}

function speakWithBrowser(text: string, speed: 'normal' | 'slow' | 'fast' = 'normal') {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()

  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'en-US'

  if (speed === 'slow') {
    u.rate = 0.62
  } else if (speed === 'fast') {
    u.rate = 1.35
  } else {
    u.rate = 1.0
  }
  u.pitch = 1.0

  const voice = getBestBrowserVoice()
  if (voice) u.voice = voice

  setTimeout(() => {
    window.speechSynthesis.speak(u)
  }, 10)
}

export function speak(text: string, speedOrRate: 'normal' | 'slow' | 'fast' | number = 'normal') {
  const clean = text.trim()
  if (!clean) return

  // Stop previous playback
  if (currentTTSAudio) {
    currentTTSAudio.pause()
    currentTTSAudio.currentTime = 0
    currentTTSAudio = null
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }

  let speed: 'normal' | 'slow' | 'fast' = 'normal'
  if (typeof speedOrRate === 'string') {
    speed = speedOrRate as 'normal' | 'slow' | 'fast'
  } else if (speedOrRate <= 0.75) {
    speed = 'slow'
  } else if (speedOrRate >= 1.2) {
    speed = 'fast'
  }

  // Use high-fidelity server TTS
  const url = `/api/tts?text=${encodeURIComponent(clean)}&speed=${speed}`
  const audio = new Audio(url)
  currentTTSAudio = audio

  audio.play().catch((err) => {
    console.warn('Server TTS failed, falling back to browser speech:', err)
    speakWithBrowser(clean, speed)
  })
}
