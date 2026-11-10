import { useEffect, useMemo, useState } from 'react'
import { api, type Folder, type Item, type Kind } from '../api'
import ItemCard from '../components/ItemCard'
import { Legend } from '../components/Pronunciation'

export default function ItemsPage({ kind }: { kind: Kind }) {
  const [items, setItems] = useState<Item[] | null>(null)
  const [folders, setFolders] = useState<Folder[]>([])
  const [folder, setFolder] = useState('')
  const [status, setStatus] = useState(kind === 'mistake' ? 'active' : '')
  const [q, setQ] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.folders().then(setFolders).catch(() => {})
  }, [])

  useEffect(() => {
    setItems(null)
    const t = setTimeout(() => {
      api
        .items({ kind, folder: folder || undefined, q: q || undefined,
                 status: status && status !== 'active' ? status : undefined })
        .then((rows) => setItems(status === 'active' ? rows.filter((r) => r.status !== 'fixed') : rows))
        .catch((e) => setError(String(e.message ?? e)))
    }, 200)
    return () => clearTimeout(t)
  }, [kind, folder, status, q])

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
        {kind === 'mistake' && items && (
          <div className="stats">
            <span className="pill status-new">{counts.new} new</span>
            <span className="pill status-practicing">{counts.practicing} practicing</span>
            <span className="pill status-fixed">{counts.fixed} fixed</span>
          </div>
        )}
      </div>

      <div className="filters">
        <input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={folder} onChange={(e) => setFolder(e.target.value)}>
          <option value="">All folders</option>
          {folders.map((f) => (
            <option key={f.name}>{f.name}</option>
          ))}
        </select>
        {kind === 'mistake' && (
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">To practice (new + practicing)</option>
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="practicing">Practicing</option>
            <option value="fixed">Fixed</option>
          </select>
        )}
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
          <ItemCard key={it.id} item={it} />
        ))}
      </div>
    </section>
  )
}
