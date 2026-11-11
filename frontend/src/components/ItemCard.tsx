import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, speak, type Item, type Status, type Token } from '../api'
import Pronunciation from './Pronunciation'

const STATUSES: { key: Status; label: string }[] = [
  { key: 'new', label: 'New' },
  { key: 'practicing', label: 'Practicing' },
  { key: 'fixed', label: 'Fixed' },
]

export default function ItemCard({ item, onChange }: { item: Item; onChange?: (i: Item) => void }) {
  const [it, setIt] = useState(item)
  const [comment, setComment] = useState(item.comment)
  const [ctxTokens, setCtxTokens] = useState<Token[] | null>(null)
  const [showCtx, setShowCtx] = useState(false)
  const [saving, setSaving] = useState(false)

  const update = async (patch: { status?: Status; comment?: string }) => {
    setSaving(true)
    try {
      const updated = await api.updateItem(it.id, patch)
      const merged = { ...it, ...updated, analysis: it.analysis, note_title: it.note_title }
      setIt(merged)
      onChange?.(merged)
    } finally {
      setSaving(false)
    }
  }

  const toggleCtx = async () => {
    if (!showCtx && !ctxTokens) setCtxTokens(await api.analyze(it.context))
    setShowCtx(!showCtx)
  }

  const before = it.context.slice(0, it.ctx_start)
  const mark = it.context.slice(it.ctx_start, it.ctx_end)
  const after = it.context.slice(it.ctx_end)

  return (
    <article className={`card kind-${it.kind} status-${it.status}`}>
      <header className="card-head">
        <h3>{it.text}</h3>
        <button className="icon" title="Listen (normal pace)" onClick={() => speak(it.text, 'normal')}>🔊</button>
        <button className="icon" title="Listen slowly (articulate)" onClick={() => speak(it.text, 'slow')}>🐢</button>
        <span className={`pill status-${it.status}`}>{it.status}</span>
        <span className="spacer" />
        <Link className="note-link" to={`/notes/${encodeURIComponent(it.note_id)}`}>
          {it.folder} › {it.note_title ?? 'note'}
        </Link>
      </header>

      {it.analysis && <Pronunciation tokens={it.analysis} />}

      <blockquote className="context">
        {before}
        <mark className={it.kind}>{mark}</mark>
        {after}
        <span className="ctx-actions">
          <button className="link-btn" onClick={() => speak(it.context)}>🔊 sentence</button>
          <button className="link-btn" onClick={toggleCtx}>
            {showCtx ? 'hide' : 'analyze'} sentence
          </button>
          <Link to="/speaking" className="link-btn">🎙️ shadow</Link>
        </span>
      </blockquote>
      {showCtx && ctxTokens && <Pronunciation tokens={ctxTokens} />}

      <footer className="card-foot">
        <div className="segmented">
          {STATUSES.map((s) => (
            <button
              key={s.key}
              className={`seg seg-${s.key} ${it.status === s.key ? 'active' : ''}`}
              disabled={saving}
              onClick={() => update({ status: s.key })}
            >
              {s.label}
            </button>
          ))}
        </div>
        <textarea
          placeholder={
            it.kind === 'vocab'
              ? 'Your notes: meaning, collocations, example sentence…'
              : 'Your notes: what went wrong, a tip, the sound to fix…'
          }
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onBlur={() => comment !== it.comment && update({ comment })}
          rows={2}
        />
      </footer>
    </article>
  )
}
