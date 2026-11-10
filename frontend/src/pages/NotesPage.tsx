import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, speak, type Item, type NoteDetail, type NoteSummary, type Run, type Token } from '../api'
import Pronunciation, { Legend } from '../components/Pronunciation'

export function NotesList() {
  const [notes, setNotes] = useState<NoteSummary[] | null>(null)
  useEffect(() => {
    api.notes().then(setNotes)
  }, [])
  const byFolder = useMemo(() => {
    const m = new Map<string, NoteSummary[]>()
    notes?.forEach((n) => m.set(n.folder, [...(m.get(n.folder) ?? []), n]))
    return m
  }, [notes])

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Notes</h1>
          <p className="muted">Read a note with your marks. Select any text to analyze it.</p>
        </div>
      </div>
      {!notes && <p className="muted">Loading…</p>}
      {notes?.length === 0 && <div className="empty"><p>No notes yet. Add a folder and sync.</p></div>}
      {[...byFolder.entries()].map(([folder, list]) => (
        <div key={folder} className="note-group">
          <h2>{folder}</h2>
          <ul className="note-list">
            {list.map((n) => (
              <li key={n.id}>
                <Link to={`/notes/${encodeURIComponent(n.id)}`}>{n.title}</Link>
                <span className="muted">
                  {n.vocab > 0 && <span className="pill kind-vocab">{n.vocab} vocab</span>}
                  {n.mistakes > 0 && <span className="pill kind-mistake">{n.mistakes} mistakes</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}

type Seg = { text: string; run: Run; start: number }

function paragraphs(text: string, runs: Run[]): Seg[][] {
  const paras: Seg[][] = [[]]
  const sorted = runs.length ? runs : [{ start: 0, end: text.length } as Run]
  for (const r of sorted) {
    let s = r.start
    const chunk = text.slice(r.start, r.end)
    const lines = chunk.split('\n')
    lines.forEach((line, i) => {
      if (i > 0) paras.push([])
      if (line) paras[paras.length - 1].push({ text: line, run: r, start: s })
      s += line.length + 1
    })
  }
  return paras
}

export function NoteView() {
  const { id = '' } = useParams()
  const [note, setNote] = useState<NoteDetail | null>(null)
  const [panel, setPanel] = useState<{ title: string; text: string; tokens: Token[]; item?: Item } | null>(null)

  useEffect(() => {
    api.note(id).then(setNote)
  }, [id])

  const itemFor = (seg: Seg, kind: 'vocab' | 'mistake') =>
    note?.items.find(
      (i) => i.kind === kind && seg.start < i.position + i.text.length && seg.start + seg.text.length > i.position,
    )

  const open = async (text: string, item?: Item) => {
    const t = text.trim()
    if (!t) return
    setPanel({ title: item ? (item.kind === 'vocab' ? 'Vocabulary' : 'Pronunciation mistake') : 'Selection', text: t, tokens: [], item })
    const tokens = await api.analyze(t)
    setPanel((p) => (p && p.text === t ? { ...p, tokens } : p))
  }

  const onMouseUp = () => {
    const sel = window.getSelection()?.toString() ?? ''
    if (sel.trim().length > 1) open(sel.slice(0, 1000))
  }

  if (!note) return <p className="muted">Loading…</p>
  const paras = paragraphs(note.text, note.runs)

  return (
    <section className="note-layout">
      <div className="note-body" onMouseUp={onMouseUp}>
        <p className="crumbs"><Link to="/notes">Notes</Link> › {note.folder}</p>
        {paras.map((segs, pi) => {
          if (!segs.length) return <div key={pi} className="para-gap" />
          const h = segs[0].run.heading
          const Tag = (h === 1 ? 'h1' : h === 2 ? 'h2' : h === 3 ? 'h3' : 'p') as 'p'
          return (
            <Tag key={pi} className="para">
              {segs.map((s, si) => {
                if (s.text === '\ufffc') return <span key={si} className="attachment">▢ attachment</span>
                const r = s.run
                const cls = [
                  r.bold && 'b', r.italic && 'i', r.strike && 's',
                  r.underline && 'mk-mistake', r.highlight && 'mk-vocab',
                ].filter(Boolean).join(' ')
                const clickable = r.underline || r.highlight
                return (
                  <span key={si} className={cls || undefined}
                    onClick={clickable ? (e) => {
                      if (window.getSelection()?.toString()) return
                      e.stopPropagation()
                      const it = itemFor(s, r.highlight ? 'vocab' : 'mistake')
                      open(it?.text ?? s.text, it)
                    } : undefined}>
                    {s.text.replaceAll('\ufffc', '▢')}
                  </span>
                )
              })}
            </Tag>
          )
        })}
      </div>

      <aside className="note-panel">
        {panel ? (
          <div className="panel-inner">
            <div className="panel-head">
              <span className={`pill ${panel.item ? `kind-${panel.item.kind}` : ''}`}>{panel.title}</span>
              <button className="icon" onClick={() => speak(panel.text)}>🔊</button>
              <button className="icon" onClick={() => speak(panel.text, 0.6)}>🐢</button>
              <button className="icon close" onClick={() => setPanel(null)}>✕</button>
            </div>
            <h3>{panel.text}</h3>
            {panel.tokens.length ? <Pronunciation tokens={panel.tokens} /> : <p className="muted">Analyzing…</p>}
            {panel.item && (
              <p className="muted small">
                Status: <b>{panel.item.status}</b>
                {panel.item.comment && <> · {panel.item.comment}</>}
              </p>
            )}
            <Legend />
          </div>
        ) : (
          <div className="panel-inner muted">
            <p>Click a <span className="mk-vocab">highlighted</span> or <span className="mk-mistake">underlined</span> phrase, or select any text, to see its IPA, stress, linking and flap-T.</p>
            <p className="small">{note.items.filter((i) => i.kind === 'vocab').length} vocab · {note.items.filter((i) => i.kind === 'mistake').length} mistakes in this note</p>
          </div>
        )}
      </aside>
    </section>
  )
}
