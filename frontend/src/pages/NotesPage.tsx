import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  api,
  speak,
  type AppleFolder,
  type AppStatus,
  type Folder,
  type Item,
  type NoteDetail,
  type NoteSummary,
  type QAItem,
  type QAEvalResult,
  type Run,
  type SyncReport,
  type Token,
} from '../api'
import Pronunciation, { Legend } from '../components/Pronunciation'
import { diffWords, useAudioRecorder, useSpeechRecognition } from '../speech'

function fmt(ts: string | null) {
  return ts ? new Date(ts).toLocaleString() : 'never'
}

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

export function NotesList() {
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [folders, setFolders] = useState<Folder[]>([])
  const [apple, setApple] = useState<AppleFolder[]>([])
  const [name, setName] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [report, setReport] = useState<SyncReport | null>(null)
  const [error, setError] = useState('')

  const [notes, setNotes] = useState<NoteSummary[] | null>(null)
  const [folder, setFolder] = useState('')
  const [q, setQ] = useState('')

  const load = useCallback(() => {
    api.folders().then(setFolders).catch(() => {})
    api.status().then(setStatus).catch(() => {})
    api.notes().then(setNotes).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    api.appleFolders().then(setApple).catch((e) => setError(`Could not list Apple Notes folders: ${e.message}`))
  }, [load])

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label)
    setError('')
    try {
      await fn()
    } catch (e) {
      setError(String((e as Error).message ?? e))
    } finally {
      setBusy(null)
      load()
    }
  }

  const add = () =>
    run('add', async () => {
      const n = name.trim()
      if (!n) return
      await api.addFolder(n)
      setName('')
      setReport(await api.sync([n]))
    })

  const tracked = new Set(folders.map((f) => f.name))
  const names = [...new Set(apple.map((a) => a.name))].filter((n) => !tracked.has(n) && n !== 'Recently Deleted')

  const availableFolders = useMemo(() => {
    return Array.from(new Set(folders.map((f) => f.name)))
  }, [folders])

  const sortedNotes = useMemo(() => {
    if (!notes) return []
    let list = notes
    if (folder) {
      list = list.filter((n) => n.folder === folder)
    }
    if (q.trim()) {
      const query = q.toLowerCase()
      list = list.filter((n) => n.title.toLowerCase().includes(query))
    }
    return sortNotesByNumber(list)
  }, [notes, folder, q])

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="section-kicker">Apple Notes & Reader</p>
          <h1>Notes</h1>
          <p className="muted">Manage Apple Notes folders, sync, and study your notes with interactive pronunciation.</p>
        </div>
        <button
          className="primary"
          disabled={!!busy || !folders.length}
          onClick={() => run('all', async () => setReport(await api.sync()))}
        >
          {busy === 'all' ? 'Syncing…' : '⟳ Sync all'}
        </button>
      </div>

      {status && (
        <div className="banner ok">
          Connected via <b>{status.reader === 'notestore' ? 'Notes database' : 'AppleScript'}</b>: bold (vocabulary) and underline (pronunciation) are both supported.
        </div>
      )}

      {/* Folders Management subsection */}
      <div className="note-group" style={{ marginBottom: '2.5rem' }}>
        <h2>Tracked Folders</h2>
        <div className="add-row">
          <input
            list="apple-folders"
            placeholder="Apple Notes folder name…"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
          />
          <datalist id="apple-folders">
            {names.map((n) => <option key={n} value={n} />)}
          </datalist>
          <button className="primary" disabled={!!busy || !name.trim()} onClick={add}>
            {busy === 'add' ? 'Adding…' : 'Add & sync'}
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        {report && (
          <div className="banner info">
            Synced via <b>{report.source === 'notestore' ? 'Notes database' : 'AppleScript'}</b>:{' '}
            {report.folders.map((f) => (
              <span key={f.folder} className="report">
                <b>{f.folder}</b> {f.notes} notes · {f.vocab} vocab · {f.mistake} pronunciation
                {f.new_items ? ` · ${f.new_items} new` : ''}
              </span>
            ))}
          </div>
        )}

        {folders.length === 0 ? (
          <div className="empty">
            <p>No folders tracked yet. Add one above, for example <i>Economic Crash Course</i>.</p>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Folder</th><th>Notes</th><th>Vocab</th><th>Pronunciation</th><th>Last synced</th><th /></tr>
            </thead>
            <tbody>
              {folders.map((f) => (
                <tr key={f.name}>
                  <td><b>{f.name}</b></td>
                  <td>{f.notes}</td>
                  <td>{f.vocab}</td>
                  <td>{f.mistakes}</td>
                  <td className="muted">{fmt(f.last_synced)}</td>
                  <td className="actions">
                    <button disabled={!!busy} onClick={() => run(f.name, async () => setReport(await api.sync([f.name])))}>
                      {busy === f.name ? 'Syncing…' : 'Sync'}
                    </button>
                    <button
                      className="danger"
                      disabled={!!busy}
                      onClick={() =>
                        confirm(`Stop tracking "${f.name}"? Your statuses and comments are kept.`) &&
                        run('rm', () => api.removeFolder(f.name))
                      }
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Notes List subsection */}
      <div className="note-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
          <h2 style={{ margin: 0 }}>
            Notes {notes ? `(${sortedNotes.length})` : ''}
          </h2>
          <div className="filters" style={{ margin: 0 }}>
            <input
              placeholder="Search notes…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              style={{ minWidth: '150px' }}
            />
            {availableFolders.length > 1 && (
              <select value={folder} onChange={(e) => setFolder(e.target.value)}>
                <option value="">All folders</option>
                {availableFolders.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            )}
          </div>
        </div>

        {!notes && <p className="muted">Loading notes…</p>}
        {notes && sortedNotes.length === 0 && (
          <div className="empty">
            <p>{q || folder ? 'No notes match the filter.' : 'No notes yet. Add a folder above and sync.'}</p>
          </div>
        )}

        {sortedNotes.length > 0 && (
          <ul className="note-list">
            {sortedNotes.map((n) => (
              <li key={n.id}>
                <Link to={`/notes/${encodeURIComponent(n.id)}`}>{n.title}</Link>
                <span className="muted">
                  {availableFolders.length > 1 && <span className="pill">{n.folder}</span>}
                  {n.vocab > 0 && <span className="pill kind-vocab">{n.vocab} vocab</span>}
                  {n.mistakes > 0 && <span className="pill kind-mistake">{n.mistakes} pronunciation</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
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

function ShadowingBox({ targetText, isLine = false }: { targetText: string; isLine?: boolean }) {
  const speech = useSpeechRecognition()
  const audio = useAudioRecorder()

  const diff = useMemo(() => {
    if (!targetText || !speech.transcript) return null
    return diffWords(targetText, speech.transcript)
  }, [targetText, speech.transcript])

  const toggle = async () => {
    if (audio.isRecording || speech.isListening) {
      audio.stopRecording()
      speech.stopListening()
    } else {
      speech.resetTranscript()
      audio.resetAudio()
      await audio.startRecording()
      speech.startListening()
    }
  }

  return (
    <div className={`shadow-box ${isLine ? 'shadow-box-line' : ''}`}>
      <div className="shadow-controls">
        <button
          className={`record-btn ${audio.isRecording ? 'recording' : ''}`}
          onClick={toggle}
        >
          {audio.isRecording ? '⏹ Stop' : '🎙️ Shadow & Speak'}
        </button>
        {audio.isRecording && (
          <span className="pulse-indicator" style={{ fontSize: '12px' }}>
            <span className="pulse-dot" /> Speaking… ({audio.duration}s)
          </span>
        )}
        {audio.audioUrl && !audio.isRecording && (
          <div className="audio-playback">
            <audio controls src={audio.audioUrl} style={{ height: '32px' }} />
          </div>
        )}
      </div>

      {speech.error && <p className="error small">{speech.error}</p>}
      {audio.error && <p className="error small">{audio.error}</p>}

      {audio.isRecording && speech.interimTranscript && (
        <p className="interim-text small" style={{ margin: '6px 0 0' }}>"{speech.interimTranscript}"</p>
      )}

      {!audio.isRecording && diff && speech.transcript && (
        <div className="diff-panel-mini">
          <div className="diff-header-mini">
            <span
              className={`pill ${diff.accuracy >= 80 ? 'status-fixed' : diff.accuracy >= 50 ? 'status-practicing' : 'status-new'}`}
              style={{ fontSize: '11px', padding: '2px 8px' }}
            >
              {diff.accuracy}% Accuracy
            </span>
            <span className="muted small">Spoken diff:</span>
          </div>
          <div className="diff-words-mini">
            {diff.diff.map((w, i) => (
              <span key={i} className={`diff-word diff-${w.status}`}>
                {w.text}{' '}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function QANotePractice({ note }: { note: NoteDetail }) {
  const [questions, setQuestions] = useState<QAItem[] | null>(null)
  const [qIdx, setQIdx] = useState(0)
  const [qaEval, setQaEval] = useState<QAEvalResult | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [showModel, setShowModel] = useState(false)

  const speech = useSpeechRecognition()
  const audio = useAudioRecorder()

  useEffect(() => {
    api
      .speakingQA(note.folder)
      .then((list) => {
        const match = list.filter((q) => q.note_id === note.id || q.note_title === note.title)
        setQuestions(match.length ? match : list)
      })
      .catch(() => setQuestions([]))
  }, [note.id, note.folder, note.title])

  const currentQ = questions?.[qIdx] ?? null

  const handleToggleRecord = async () => {
    if (audio.isRecording || speech.isListening) {
      audio.stopRecording()
      speech.stopListening()

      if (currentQ) {
        setEvaluating(true)
        try {
          const res = await api.evaluateAnswer({
            question: currentQ,
            spoken_text: speech.transcript || speech.interimTranscript || 'No speech detected',
            duration_sec: audio.duration,
          })
          setQaEval(res)
        } catch (e) {
          console.error(e)
        } finally {
          setEvaluating(false)
        }
      }
    } else {
      setQaEval(null)
      setShowModel(false)
      speech.resetTranscript()
      audio.resetAudio()
      await audio.startRecording()
      speech.startListening()
    }
  }

  const nextQ = () => {
    if (!questions?.length) return
    audio.resetAudio()
    speech.resetTranscript()
    setQaEval(null)
    setShowModel(false)
    setQIdx((prev) => (prev + 1) % questions.length)
  }

  const prevQ = () => {
    if (!questions?.length) return
    audio.resetAudio()
    speech.resetTranscript()
    setQaEval(null)
    setShowModel(false)
    setQIdx((prev) => (prev - 1 + questions.length) % questions.length)
  }

  if (!questions) return <p className="muted">Loading questions…</p>
  if (questions.length === 0) {
    return (
      <div className="empty">
        <p>No parsed questions found in this note. Switch to Note Transcript view above to view note text.</p>
      </div>
    )
  }

  if (!currentQ) return null

  return (
    <div className="card speaking-card" style={{ marginTop: '16px' }}>
      <header className="card-head">
        <span className="pill status-practicing">
          Question {qIdx + 1} of {questions.length}
        </span>
        <span className="pill" style={{ background: 'var(--paper-deep)' }}>
          {currentQ.topic}
        </span>
        {currentQ.subtopic !== currentQ.topic && (
          <span className="pill" style={{ background: 'var(--surface-blue)' }}>
            {currentQ.subtopic}
          </span>
        )}
      </header>

      <div className="speaking-target">
        <p className="micro-kicker">Question Prompt:</p>
        <h2 className="qa-prompt">{currentQ.question}</h2>
        <div className="audio-actions">
          <button onClick={() => speak(currentQ.question)} title="Listen to question spoken in US English">
            🔊 Listen to Question
          </button>
        </div>
      </div>

      <div className="record-panel">
        <div className="record-controls">
          <button
            className={`record-btn ${audio.isRecording ? 'recording' : ''}`}
            onClick={handleToggleRecord}
            disabled={evaluating}
          >
            {evaluating
              ? 'Evaluating speech…'
              : audio.isRecording
              ? '⏹ Finish Answer & Evaluate'
              : '🎙️ Record Spoken Answer'}
          </button>

          {audio.isRecording && (
            <span className="pulse-indicator">
              <span className="pulse-dot" /> Speaking… ({audio.duration}s)
            </span>
          )}

          {audio.audioUrl && !audio.isRecording && (
            <div className="audio-playback">
              <span className="muted">Your answer recording:</span>
              <audio controls src={audio.audioUrl} />
            </div>
          )}
        </div>

        {speech.error && <p className="error">{speech.error}</p>}
        {audio.error && <p className="error">{audio.error}</p>}

        {audio.isRecording && (
          <div className="transcript-live-box">
            <p className="micro-kicker">Live Transcription:</p>
            <p className="transcript-text">
              {speech.transcript}{' '}
              <span className="interim-text">{speech.interimTranscript}</span>
            </p>
          </div>
        )}

        {!audio.isRecording && qaEval && (
          <div className="qa-eval-result">
            <div className="eval-score-banner">
              <div>
                <h3>{qaEval.summary}</h3>
                <p className="muted" style={{ margin: '4px 0 0' }}>
                  {qaEval.pace_feedback}
                </p>
              </div>
              <div className="score-badge">
                <span className="score-num">{qaEval.coverage_pct}%</span>
                <span className="score-label">Concepts</span>
              </div>
            </div>

            <div className="eval-stats-row">
              <span className="pill">Words: {qaEval.word_count}</span>
              <span className="pill">Duration: {qaEval.duration_sec}s</span>
              <span className="pill">Pace: {qaEval.wpm} WPM</span>
              <span className="pill status-fixed">
                Covered: {qaEval.covered_count} / {qaEval.total_points}
              </span>
            </div>

            <div className="transcript-spoken-box">
              <p className="micro-kicker">Your Spoken Answer:</p>
              <p className="transcript-text">"{qaEval.spoken_text}"</p>
            </div>

            <div className="concepts-checklist">
              <p className="micro-kicker">Required Key Concepts Coverage:</p>
              {qaEval.key_points.map((kp, idx) => (
                <div key={idx} className={`concept-item concept-${kp.status}`}>
                  <div className="concept-head">
                    <span className={`pill concept-status-${kp.status}`}>
                      {kp.status === 'covered'
                        ? '✓ Covered'
                        : kp.status === 'partial'
                        ? '~ Partially Addressed'
                        : '✕ Missed'}
                    </span>
                    <strong>{kp.title}</strong>
                  </div>
                  <p className="concept-desc">{kp.description}</p>
                  {kp.matched_terms && kp.matched_terms.length > 0 && (
                    <p className="concept-matches">
                      <span className="muted">Matched keywords:</span>{' '}
                      {kp.matched_terms.map((t, ti) => (
                        <code key={ti} className="match-tag">
                          {t}
                        </code>
                      ))}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {!audio.isRecording && (
          <div style={{ marginTop: '1rem' }}>
            <button className="link-btn" onClick={() => setShowModel(!showModel)}>
              {showModel ? '▼ Hide Key Points & Model Guide' : '▶ Reveal Key Points & Model Guide'}
            </button>
            {showModel && (
              <div className="model-answer-box">
                <h4 style={{ margin: '0 0 8px' }}>Target Concepts for this Question:</h4>
                <ul className="model-points-list">
                  {currentQ.key_points.map((kp, i) => (
                    <li key={i}>
                      <strong>{kp.title}:</strong> {kp.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      <footer className="card-foot" style={{ justifyContent: 'space-between', display: 'flex' }}>
        <button onClick={prevQ} disabled={qIdx === 0}>
          ← Previous Question
        </button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => {
              audio.resetAudio()
              speech.resetTranscript()
              setQaEval(null)
            }}
          >
            Clear / Retry
          </button>
          <button
            className="primary"
            onClick={nextQ}
            disabled={qIdx >= questions.length - 1}
          >
            Next Question →
          </button>
        </div>
      </footer>
    </div>
  )
}

export function NoteView() {
  const { id = '' } = useParams()
  const [note, setNote] = useState<NoteDetail | null>(null)
  const [partIdx, setPartIdx] = useState(0)
  const [mode, setMode] = useState<'side' | 'line'>('side')
  const [qaViewMode, setQaViewMode] = useState<'practice' | 'transcript'>('practice')
  const [activeShadowLine, setActiveShadowLine] = useState<number | null>(null)
  const [lineIpaCache, setLineIpaCache] = useState<Record<string, Token[]>>({})
  const [loadingLines, setLoadingLines] = useState(false)
  const [panel, setPanel] = useState<{ title: string; text: string; tokens: Token[]; item?: Item } | null>(null)

  useEffect(() => {
    setNote(null)
    setPartIdx(0)
    setPanel(null)
    setActiveShadowLine(null)
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

  const isQA = Boolean(note && /questions?\s*(&|and)?\s*answers?/i.test(note.title))
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
            {isQA
              ? 'Oral Exam & Conceptual Interview Practice'
              : parts.length > 1
              ? `Part ${safePartIdx + 1} of ${parts.length} · ${partVocabCount} vocab · ${partPronCount} pronunciation in this part`
              : `${note.items.filter((i) => i.kind === 'vocab').length} vocab · ${note.items.filter((i) => i.kind === 'mistake').length} pronunciation in this note`}
          </p>
        </div>

        {isQA ? (
          <div className="view-mode-toggle" role="group" aria-label="QA display mode">
            <button
              type="button"
              aria-pressed={qaViewMode === 'practice'}
              onClick={() => setQaViewMode('practice')}
            >
              💬 Practice Q&amp;A
            </button>
            <button
              type="button"
              aria-pressed={qaViewMode === 'transcript'}
              onClick={() => setQaViewMode('transcript')}
            >
              📄 Note Transcript
            </button>
          </div>
        ) : (
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
        )}
      </div>

      {isQA && qaViewMode === 'practice' ? (
        <QANotePractice note={note} />
      ) : (
        <>
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
                          <button
                            className={`icon ${activeShadowLine === pi ? 'active' : ''}`}
                            title="Practice shadowing this line"
                            onClick={() => setActiveShadowLine(activeShadowLine === pi ? null : pi)}
                          >
                            🎙️
                          </button>
                        </div>
                      </div>
                      {tokens && tokens.length > 0 && <Pronunciation tokens={tokens} />}
                      {activeShadowLine === pi && <ShadowingBox key={cleaned} targetText={cleaned} isLine />}
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
                    <ShadowingBox key={panel.text} targetText={panel.text} />
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
        </>
      )}
    </section>
  )
}
