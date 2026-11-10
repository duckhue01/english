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
          <p className="section-kicker">Interactive Transcript Reader</p>
          <h1>Notes</h1>
          <p className="muted">Read a note part by part, switch to line-by-line IPA, or select any text to analyze.</p>
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
                  {n.mistakes > 0 && <span className="pill kind-mistake">{n.mistakes} pronunciation</span>}
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
type Para = { segs: Seg[]; text: string; heading: number }

const SEP_RE = /^\s*={3,}\s*$/

function buildParts(noteTitle: string, text: string, runs: Run[]): Para[][] {
  const rawParas: Seg[][] = [[]]
  const sorted = runs.length ? runs : [{ start: 0, end: text.length } as Run]
  for (const r of sorted) {
    let s = r.start
    const chunk = text.slice(r.start, r.end)
    const lines = chunk.split('\n')
    lines.forEach((line, i) => {
      if (i > 0) rawParas.push([])
      if (line) rawParas[rawParas.length - 1].push({ text: line, run: r, start: s })
      s += line.length + 1
    })
  }

  const paras: Para[] = rawParas.map((segs) => ({
    segs,
    text: segs.map((s) => s.text).join(''),
    heading: segs[0]?.run.heading ?? 0,
  }))

  // Skip the leading title paragraph if it duplicates note.title
  let startIdx = 0
  while (startIdx < paras.length && !paras[startIdx].text.trim()) startIdx += 1
  if (
    startIdx < paras.length &&
    (paras[startIdx].heading === 1 || paras[startIdx].text.trim() === noteTitle.trim())
  ) {
    startIdx += 1
  }

  // Split into parts separated by ====================================================== (or any ===+ line)
  const parts: Para[][] = []
  let current: Para[] = []
  for (let i = startIdx; i < paras.length; i++) {
    const p = paras[i]
    if (SEP_RE.test(p.text)) {
      if (current.some((x) => x.text.trim())) {
        parts.push(trimEmptyParas(current))
      }
      current = []
    } else {
      current.push(p)
    }
  }
  if (current.some((x) => x.text.trim())) {
    parts.push(trimEmptyParas(current))
  }
  return parts.length ? parts : [[]]
}

function trimEmptyParas(list: Para[]): Para[] {
  let a = 0
  let b = list.length
  while (a < b && !list[a].text.trim()) a += 1
  while (b > a && !list[b - 1].text.trim()) b -= 1
  return list.slice(a, b)
}

function cleanLineForIpa(text: string): string {
  return text.replaceAll('\ufffc', '').trim()
}

export function NoteView() {
  const { id = '' } = useParams()
  const [note, setNote] = useState<NoteDetail | null>(null)
  const [partIdx, setPartIdx] = useState(0)
  const [mode, setMode] = useState<'side' | 'line'>('side')
  const [lineIpaCache, setLineIpaCache] = useState<Record<string, Token[]>>({})
  const [loadingLines, setLoadingLines] = useState(false)
  const [panel, setPanel] = useState<{ title: string; text: string; tokens: Token[]; item?: Item } | null>(null)

  useEffect(() => {
    setNote(null)
    setPartIdx(0)
    setPanel(null)
    api.note(id).then(setNote)
  }, [id])

  const parts = useMemo(
    () => (note ? buildParts(note.title, note.text, note.runs) : [[]]),
    [note],
  )
  const safePartIdx = Math.min(partIdx, Math.max(0, parts.length - 1))
  const currentParas = parts[safePartIdx] ?? []

  // Fetch line-by-line IPA when in 'line' mode for the active part
  useEffect(() => {
    if (mode !== 'line' || !currentParas.length) return
    const missing = Array.from(
      new Set(
        currentParas
          .map((p) => cleanLineForIpa(p.text))
          .filter((t) => t.length > 0 && !lineIpaCache[t]),
      ),
    )
    if (!missing.length) return
    let cancelled = false
    setLoadingLines(true)
    api
      .analyzeBatch(missing)
      .then((results) => {
        if (cancelled) return
        setLineIpaCache((prev) => {
          const next = { ...prev }
          missing.forEach((t, idx) => {
            next[t] = results[idx] ?? []
          })
          return next
        })
      })
      .finally(() => {
        if (!cancelled) setLoadingLines(false)
      })
    return () => {
      cancelled = true
    }
  }, [mode, currentParas, lineIpaCache])

  const itemFor = (seg: Seg, kind: 'vocab' | 'mistake') =>
    note?.items.find(
      (i) => i.kind === kind && seg.start < i.position + i.text.length && seg.start + seg.text.length > i.position,
    )

  const open = async (text: string, item?: Item) => {
    const t = text.trim()
    if (!t) return
    setPanel({
      title: item ? (item.kind === 'vocab' ? 'Vocabulary' : 'Pronunciation') : 'Selection',
      text: t,
      tokens: [],
      item,
    })
    const tokens = await api.analyze(t)
    setPanel((p) => (p && p.text === t ? { ...p, tokens } : p))
  }

  const onMouseUp = () => {
    const sel = window.getSelection()?.toString() ?? ''
    if (sel.trim().length > 1) open(sel.slice(0, 1000))
  }

  const renderSegs = (segs: Seg[]) =>
    segs.map((s, si) => {
      if (s.text === '\ufffc') return <span key={si} className="attachment">▢ attachment</span>
      const r = s.run
      const vocabItem = itemFor(s, 'vocab')
      const mistakeItem = itemFor(s, 'mistake')
      const isVocab = Boolean(vocabItem)
      const isMistake = Boolean(mistakeItem) || r.underline
      const cls = [
        r.bold && 'b',
        r.italic && 'i',
        r.strike && 's',
        isMistake && 'mk-mistake',
        isVocab && 'mk-vocab',
      ]
        .filter(Boolean)
        .join(' ')
      const clickable = isMistake || isVocab
      return (
        <span
          key={si}
          className={cls || undefined}
          onClick={
            clickable
              ? (e) => {
                  if (window.getSelection()?.toString()) return
                  e.stopPropagation()
                  const it = vocabItem ?? mistakeItem
                  open(it?.text ?? s.text, it)
                }
              : undefined
          }
        >
          {s.text.replaceAll('\ufffc', '▢')}
        </span>
      )
    })

  if (!note) return <p className="muted">Loading…</p>

  const partStartOffset =
    currentParas.find((p) => p.segs.length > 0)?.segs[0]?.start ?? 0
  const lastSegs = [...currentParas].reverse().find((p) => p.segs.length > 0)?.segs
  const partEndOffset = lastSegs
    ? lastSegs[lastSegs.length - 1].start + lastSegs[lastSegs.length - 1].text.length
    : note.text.length
  const partVocabCount = note.items.filter(
    (i) => i.kind === 'vocab' && i.position >= partStartOffset && i.position <= partEndOffset,
  ).length
  const partPronCount = note.items.filter(
    (i) => i.kind === 'mistake' && i.position >= partStartOffset && i.position <= partEndOffset,
  ).length

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="crumbs">
            <Link to="/notes">Notes</Link> › {note.folder}
          </p>
          <h1>{note.title}</h1>
          <p className="muted small">
            {parts.length > 1
              ? `Part ${safePartIdx + 1} of ${parts.length} · ${partVocabCount} vocab · ${partPronCount} pronunciation in this part`
              : `${note.items.filter((i) => i.kind === 'vocab').length} vocab · ${note.items.filter((i) => i.kind === 'mistake').length} pronunciation in this note`}
          </p>
        </div>

        <div className="view-mode-toggle" role="group" aria-label="Note display mode">
          <button
            type="button"
            aria-pressed={mode === 'side'}
            onClick={() => setMode('side')}
          >
            Select &amp; Side Panel
          </button>
          <button
            type="button"
            aria-pressed={mode === 'line'}
            onClick={() => setMode('line')}
          >
            Line-by-Line IPA
          </button>
        </div>
      </div>

      {parts.length > 1 && (
        <div className="part-bar">
          <button
            disabled={safePartIdx === 0}
            onClick={() => setPartIdx((i) => Math.max(0, i - 1))}
          >
            ← Prev
          </button>
          <div className="part-tabs">
            {parts.map((_, idx) => (
              <button
                key={idx}
                className={idx === safePartIdx ? 'active' : ''}
                onClick={() => setPartIdx(idx)}
              >
                Part {idx + 1}
              </button>
            ))}
          </div>
          <button
            disabled={safePartIdx >= parts.length - 1}
            onClick={() => setPartIdx((i) => Math.min(parts.length - 1, i + 1))}
          >
            Next →
          </button>
        </div>
      )}

      {mode === 'line' ? (
        <div className="line-ipa-container">
          <Legend />
          {loadingLines && <p className="muted small">Analyzing lines…</p>}
          <div className="line-ipa-list">
            {currentParas.map((p, pi) => {
              const cleaned = cleanLineForIpa(p.text)
              if (!cleaned) return null
              const tokens = lineIpaCache[cleaned]
              const Tag = (p.heading === 1 ? 'h1' : p.heading === 2 ? 'h2' : p.heading === 3 ? 'h3' : 'p') as 'p'
              return (
                <article key={pi} className="line-ipa-row">
                  <div className="line-ipa-head">
                    <Tag className="para">{renderSegs(p.segs)}</Tag>
                    <div className="line-ipa-actions">
                      <button className="icon" title="Listen (US voice)" onClick={() => speak(cleaned)}>🔊</button>
                      <button className="icon" title="Listen slowly" onClick={() => speak(cleaned, 0.6)}>🐢</button>
                    </div>
                  </div>
                  {tokens && tokens.length > 0 && <Pronunciation tokens={tokens} />}
                </article>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="note-layout">
          <div className="note-body" onMouseUp={onMouseUp}>
            {currentParas.map((p, pi) => {
              if (!p.segs.length) return <div key={pi} className="para-gap" />
              const Tag = (p.heading === 1 ? 'h1' : p.heading === 2 ? 'h2' : p.heading === 3 ? 'h3' : 'p') as 'p'
              return (
                <Tag key={pi} className="para">
                  {renderSegs(p.segs)}
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
                <p>
                  Click a <span className="mk-vocab">bold vocabulary</span> or{' '}
                  <span className="mk-mistake">underlined pronunciation</span> phrase, or select any text, to see its
                  IPA, stress, linking and flap-T.
                </p>
                <p className="small">
                  {partVocabCount} vocab · {partPronCount} pronunciation in this part
                </p>
              </div>
            )}
          </aside>
        </div>
      )}

      {parts.length > 1 && (
        <div className="part-bar part-bar-bottom">
          <button
            disabled={safePartIdx === 0}
            onClick={() => {
              setPartIdx((i) => Math.max(0, i - 1))
              window.scrollTo({ top: 0, behavior: 'smooth' })
            }}
          >
            ← Prev Part
          </button>
          <span className="muted small">
            Part {safePartIdx + 1} of {parts.length}
          </span>
          <button
            disabled={safePartIdx >= parts.length - 1}
            onClick={() => {
              setPartIdx((i) => Math.min(parts.length - 1, i + 1))
              window.scrollTo({ top: 0, behavior: 'smooth' })
            }}
          >
            Next Part →
          </button>
        </div>
      )}
    </section>
  )
}
