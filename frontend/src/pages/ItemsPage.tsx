import { useEffect, useMemo, useState } from 'react'
import { api, type Folder, type Item, type Kind, type NoteSummary } from '../api'
import ItemCard from '../components/ItemCard'
import { Legend } from '../components/Pronunciation'

function extractNoteNumber(title: string): number | null {
  const m = title.trim().match(/^(\d+)/)
  return m ? parseInt(m[1], 10) : null
}

function sortNotesByNumber(list: NoteSummary[]): NoteSummary[] {
  return [...list].sort((a, b) => {
    const numA = extractNoteNumber(a.title)
    const numB = extractNoteNumber(b.title)
    if (numA !== null && numB !== null) {
      if (numA !== numB) return numA - numB
      return a.title.localeCompare(b.title, undefined, { numeric: true, sensitivity: 'base' })
    }
    if (numA !== null) return -1
    if (numB !== null) return 1
    return a.title.localeCompare(b.title, undefined, { numeric: true, sensitivity: 'base' })
  })
}

export default function ItemsPage({ kind }: { kind: Kind }) {
  const [items, setItems] = useState<Item[] | null>(null)
  const [folders, setFolders] = useState<Folder[]>([])
  const [notes, setNotes] = useState<NoteSummary[]>([])
  const [folder, setFolder] = useState('')
  const [noteId, setNoteId] = useState('')
  const [status, setStatus] = useState('active')
  const [q, setQ] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.folders().then(setFolders).catch(() => {})
    api.notes().then(setNotes).catch(() => {})
  }, [])

  const availableNotes = useMemo(() => {
    const list = folder ? notes.filter((n) => n.folder === folder) : notes
    return sortNotesByNumber(list)
  }, [notes, folder])

  const onFolderChange = (newFolder: string) => {
    setFolder(newFolder)
    if (noteId) {
      const currentNote = notes.find((n) => n.id === noteId)
      if (newFolder && currentNote && currentNote.folder !== newFolder) {
        setNoteId('')
      }
    }
  }

  useEffect(() => {
    setItems(null)
    const t = setTimeout(() => {
      api
        .items({
          kind,
          folder: folder || undefined,
          note_id: noteId || undefined,
          q: q || undefined,
          status: status && status !== 'active' ? status : undefined,
        })
        .then((rows) => setItems(status === 'active' ? rows.filter((r) => r.status !== 'fixed') : rows))
        .catch((e) => setError(String(e.message ?? e)))
    }, 200)
    return () => clearTimeout(t)
  }, [kind, folder, noteId, status, q])

  const counts = useMemo(() => {
    const c = { new: 0, practicing: 0, fixed: 0 }
    items?.forEach((i) => (c[i.status] += 1))
    return c
  }, [items])

  const title = kind === 'vocab' ? 'New vocabulary' : 'Pronunciation'
  const hint =
    kind === 'vocab' ? 'Words you bolded in Apple Notes.' : 'Words and phrases you underlined in Apple Notes.'

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="section-kicker">{kind === 'vocab' ? 'Bolded Words & Idioms' : 'Underlined Words & Phrases'}</p>
          <h1>{title}</h1>
          <p className="muted">{hint}</p>
        </div>
        {items && (
          <div className="stats">
            <span className="pill status-new">{counts.new} new</span>
            <span className="pill status-practicing">{counts.practicing} practicing</span>
            <span className="pill status-fixed">{counts.fixed} fixed</span>
          </div>
        )}
      </div>

      <div className="filters">
        <input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={folder} onChange={(e) => onFolderChange(e.target.value)}>
          <option value="">All folders</option>
          {folders.map((f) => (
            <option key={f.name} value={f.name}>{f.name}</option>
          ))}
        </select>
        <select value={noteId} onChange={(e) => setNoteId(e.target.value)}>
          <option value="">All notes</option>
          {availableNotes.map((n) => (
            <option key={n.id} value={n.id}>
              {n.title}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="active">To practice (new + practicing)</option>
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="practicing">Practicing</option>
          <option value="fixed">Fixed</option>
        </select>
      </div>

      <Legend />

      {error && <p className="error">{error}</p>}
      {!items && !error && <p className="muted">Loading…</p>}
      {items && items.length === 0 && (
        <div className="empty">
          {kind === 'vocab' ? (
            <p>
              No vocabulary yet. Bold full words in your notes, then <b>Sync</b>.
            </p>
          ) : (
            <p>Nothing here. Underline words or phrases to practice in your notes, then <b>Sync</b>.</p>
          )}
        </div>
      )}
      <div className="cards">
        {items?.map((it) => (
          <ItemCard
            key={it.id}
            item={it}
            onChange={(updated) => {
              setItems((prev) =>
                prev ? prev.map((x) => (x.id === updated.id ? updated : x)) : null,
              )
            }}
          />
        ))}
      </div>
    </section>
  )
}
