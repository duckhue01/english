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

const qs = (p: Record<string, string | undefined>) => {
  const s = new URLSearchParams()
  Object.entries(p).forEach(([k, v]) => v && s.set(k, v))
  const str = s.toString()
  return str ? `?${str}` : ''
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
  items: (p: { kind?: Kind; status?: string; folder?: string; q?: string }) =>
    req<Item[]>(`/items${qs(p)}`),
  updateItem: (id: string, patch: { status?: Status; comment?: string }) =>
    req<Item>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  notes: (folder?: string) => req<NoteSummary[]>(`/notes${qs({ folder })}`),
  note: (id: string) => req<NoteDetail>(`/notes/${encodeURIComponent(id)}`),
  analyze: (text: string) =>
    req<Token[]>('/analyze', { method: 'POST', body: JSON.stringify({ text }) }),
  analyzeBatch: (texts: string[]) =>
    req<Token[][]>('/analyze-batch', { method: 'POST', body: JSON.stringify({ texts }) }),
}

export function speak(text: string, rate = 0.9) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = 'en-US'
  u.rate = rate
  const voice = window.speechSynthesis
    .getVoices()
    .find((v) => v.lang === 'en-US' && /Samantha|Alex|Ava|Allison|Google US/i.test(v.name))
  if (voice) u.voice = voice
  window.speechSynthesis.speak(u)
}
