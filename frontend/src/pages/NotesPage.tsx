import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
  type PronEvaluationResult,
  type QAItem,
  type QAEvalResult,
  type Run,
  type SyncReport,
  type Token,
  type WordToken,
} from '../api'
import Pronunciation, { Legend } from '../components/Pronunciation'
import { diffWords, useAudioRecorder, useSpeechRecognition } from '../speech'

function fmt(ts: string | null) {
  if (!ts) return 'never'
  const d = new Date(ts)
  const now = Date.now()
  const diffSec = Math.floor((now - d.getTime()) / 1000)
  if (diffSec < 60) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return d.toLocaleDateString()
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
  const [q, setQ] = useState('')
  const [collapsedFolders, setCollapsedFolders] = useState<Record<string, boolean>>({})

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

  const toggleFolder = (folderName: string) => {
    setCollapsedFolders((prev) => ({
      ...prev,
      [folderName]: !prev[folderName],
    }))
  }

  const allCollapsed = useMemo(() => {
    return folders.length > 0 && folders.every((f) => collapsedFolders[f.name])
  }, [folders, collapsedFolders])

  const toggleAllFolders = () => {
    const nextState = !allCollapsed
    const nextMap: Record<string, boolean> = {}
    folders.forEach((f) => {
      nextMap[f.name] = nextState
    })
    setCollapsedFolders(nextMap)
  }

  const latestSyncTimestamp = useMemo(() => {
    let latest: string | null = null
    folders.forEach((f) => {
      if (f.last_synced) {
        if (!latest || new Date(f.last_synced).getTime() > new Date(latest).getTime()) {
          latest = f.last_synced
        }
      }
    })
    return latest
  }, [folders])

  const treeData = useMemo(() => {
    if (!folders.length) return []
    return folders
      .map((f) => {
        let folderNotes = notes?.filter((n) => n.folder === f.name) ?? []
        if (q.trim()) {
          const query = q.toLowerCase()
          folderNotes = folderNotes.filter((n) => n.title.toLowerCase().includes(query))
        }
        return {
          folder: f,
          notes: sortNotesByNumber(folderNotes),
          matchesSearch:
            !q.trim() ||
            folderNotes.length > 0 ||
            f.name.toLowerCase().includes(q.toLowerCase()),
        }
      })
      .filter((g) => g.matchesSearch)
  }, [folders, notes, q])

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="section-kicker">Apple Notes &amp; Tree</p>
          <h1>Notes</h1>
          <p className="muted">
            Tracked folders, notes tree hierarchy, and interactive pronunciation study.
          </p>
        </div>

        <div className="sync-all-container">
          <button
            className={`primary sync-all-btn ${busy === 'all' ? 'is-syncing' : ''}`}
            disabled={!!busy || !folders.length}
            onClick={() => run('all', async () => setReport(await api.sync()))}
          >
            {busy === 'all' ? 'Syncing Apple Notes…' : 'Sync all'}
          </button>
          {folders.length > 0 && (
            <div className="sync-status-meta">
              <span>Last synced: {fmt(latestSyncTimestamp)}</span>
              <span>·</span>
              <span className="reader-tag">
                {status?.reader === 'notestore' ? 'Notes DB' : 'AppleScript'}
              </span>
            </div>
          )}
        </div>
      </div>

      {status && (
        <div className="banner ok">
          Connected via <b>{status.reader === 'notestore' ? 'Notes database' : 'AppleScript'}</b>: bold (vocabulary) and underline (pronunciation) are both supported.
        </div>
      )}

      {/* Folder & Notes Tree Section */}
      <div className="note-group">
        <div className="tree-toolbar">
          <div className="add-row">
            <input
              list="apple-folders"
              placeholder="Add Apple Notes folder…"
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

          <div className="tree-filters">
            <input
              placeholder="Search tree…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              style={{ minWidth: '160px' }}
            />
            {folders.length > 0 && (
              <button
                className="seg"
                onClick={toggleAllFolders}
                title={allCollapsed ? 'Expand all folders' : 'Collapse all folders'}
              >
                {allCollapsed ? '▼ Expand all' : '▲ Collapse all'}
              </button>
            )}
          </div>
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
          <div className="folder-notes-tree">
            {treeData.map((group) => {
              const isCollapsed = Boolean(collapsedFolders[group.folder.name])
              return (
                <div key={group.folder.name} className="tree-folder-node">
                  <div
                    className="tree-folder-head"
                    onClick={() => toggleFolder(group.folder.name)}
                  >
                    <div className="tree-folder-main">
                      <span className="tree-folder-chevron">
                        {isCollapsed ? '▶' : '▼'}
                      </span>
                      <span style={{ fontSize: '15px' }}>📁</span>
                      <span className="tree-folder-name">{group.folder.name}</span>
                      <span className="pill">{group.folder.notes} notes</span>
                      {group.folder.vocab > 0 && (
                        <span className="pill kind-vocab">{group.folder.vocab} vocab</span>
                      )}
                      {group.folder.mistakes > 0 && (
                        <span className="pill kind-mistake">
                          {group.folder.mistakes} pron
                        </span>
                      )}
                      <span className="muted small" style={{ marginLeft: '4px' }}>
                        {fmt(group.folder.last_synced)}
                      </span>
                    </div>

                    <div
                      className="tree-folder-actions"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        className="icon"
                        disabled={!!busy}
                        title={`Sync folder "${group.folder.name}"`}
                        onClick={() =>
                          run(group.folder.name, async () =>
                            setReport(await api.sync([group.folder.name]))
                          )
                        }
                      >
                        <span className={`sync-icon ${busy === group.folder.name ? 'spin' : ''}`}>⟳</span>
                      </button>
                      <button
                        className="icon danger"
                        disabled={!!busy}
                        title={`Remove "${group.folder.name}"`}
                        onClick={() =>
                          confirm(`Stop tracking "${group.folder.name}"? Your statuses and comments are kept.`) &&
                          run('rm', () => api.removeFolder(group.folder.name))
                        }
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {!isCollapsed && (
                    <ul className="tree-notes-branch">
                      {group.notes.length === 0 ? (
                        <li className="muted small tree-empty">
                          {q ? 'No notes match your filter.' : 'No notes in this folder yet. Sync to fetch.'}
                        </li>
                      ) : (
                        group.notes.map((n) => {
                          const isQA = /questions?\s*(&|and)?\s*answers?/i.test(n.title)
                          return (
                            <li key={n.id} className="tree-note-item">
                              <div className="tree-note-link-wrap">
                                <span className="tree-note-icon">
                                  {isQA ? '💬' : '📄'}
                                </span>
                                <Link
                                  className="tree-note-title"
                                  to={`/notes/${encodeURIComponent(n.id)}`}
                                >
                                  {n.title}
                                </Link>
                              </div>

                              <div className="tree-note-meta">
                                {isQA && (
                                  <span className="pill status-practicing" style={{ fontSize: '11px' }}>
                                    Oral Exam / Q&amp;A
                                  </span>
                                )}
                                {n.vocab > 0 && (
                                  <span className="pill kind-vocab" style={{ fontSize: '11px' }}>
                                    {n.vocab} vocab
                                  </span>
                                )}
                                {n.mistakes > 0 && (
                                  <span className="pill kind-mistake" style={{ fontSize: '11px' }}>
                                    {n.mistakes} pron
                                  </span>
                                )}
                              </div>
                            </li>
                          )
                        })
                      )}
                    </ul>
                  )}
                </div>
              )
            })}
          </div>
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

function ShadowingBox({
  targetText,
  isLine = false,
  isWord = false,
}: {
  targetText: string
  isLine?: boolean
  isWord?: boolean
}) {
  const speech = useSpeechRecognition()
  const audio = useAudioRecorder()
  const [evalResult, setEvalResult] = useState<PronEvaluationResult | null>(null)
  const [scoring, setScoring] = useState(false)
  const [activeTip, setActiveTip] = useState<string | null>(null)
  const [isPlayingMine, setIsPlayingMine] = useState(false)
  const playerRef = useRef<HTMLAudioElement | null>(null)

  const diff = useMemo(() => {
    if (!targetText || !speech.transcript) return null
    return diffWords(targetText, speech.transcript)
  }, [targetText, speech.transcript])

  useEffect(() => {
    if (audio.audioBlob && !audio.isRecording) {
      setScoring(true)
      setActiveTip(null)
      api
        .scoreAudio(audio.audioBlob, targetText, 'both', 0.5)
        .then(setEvalResult)
        .catch((e) => console.error('Pron scoring error:', e))
        .finally(() => setScoring(false))
    }
  }, [audio.audioBlob, audio.isRecording, targetText])

  const stop = useCallback(() => {
    if (audio.isRecording || speech.isListening) {
      audio.stopRecording()
      speech.stopListening()
    }
  }, [audio, speech])

  // Auto-finish recording when speech completes to eliminate manual stop step
  useEffect(() => {
    if (!audio.isRecording) return

    if (isWord) {
      if (speech.transcript || speech.interimTranscript) {
        const timer = setTimeout(() => {
          stop()
        }, 700)
        return () => clearTimeout(timer)
      }
      if (audio.duration >= 2.8) {
        stop()
      }
    } else {
      if (speech.transcript) {
        const timer = setTimeout(() => {
          stop()
        }, 1200)
        return () => clearTimeout(timer)
      }
      if (audio.duration >= 14) {
        stop()
      }
    }
  }, [audio.isRecording, audio.duration, speech.transcript, speech.interimTranscript, isWord, stop])

  const startRecording = async () => {
    if (playerRef.current) {
      playerRef.current.pause()
      setIsPlayingMine(false)
    }
    setEvalResult(null)
    setActiveTip(null)
    speech.resetTranscript()
    audio.resetAudio()
    await audio.startRecording()
    speech.startListening()
  }

  const toggle = async () => {
    if (audio.isRecording || speech.isListening) {
      stop()
    } else {
      await startRecording()
    }
  }

  const playMine = () => {
    if (!audio.audioUrl) return
    if (!playerRef.current) {
      playerRef.current = new Audio(audio.audioUrl)
      playerRef.current.onended = () => setIsPlayingMine(false)
      playerRef.current.onpause = () => setIsPlayingMine(false)
    } else {
      playerRef.current.src = audio.audioUrl
    }
    if (isPlayingMine) {
      playerRef.current.pause()
      setIsPlayingMine(false)
    } else {
      playerRef.current.play().then(() => setIsPlayingMine(true)).catch(() => {})
    }
  }

  return (
    <div className={`shadow-box ${isLine ? 'shadow-box-line' : ''} ${isWord ? 'shadow-box-word' : ''}`}>
      <div className="shadow-controls">
        {audio.isRecording ? (
          <>
            <button className="record-btn recording" onClick={stop}>
              ⏹ Done
            </button>
            <span className="pulse-indicator" style={{ fontSize: '11px' }}>
              <span className="pulse-dot" /> Speaking… ({audio.duration}s) · auto-stops
            </span>
          </>
        ) : !audio.audioUrl ? (
          <button className="record-btn" onClick={toggle}>
            {isWord ? '🎙️ Record Word' : '🎙️ Shadow & Speak'}
          </button>
        ) : (
          <div className="instant-review-bar">
            <button
              className="instant-audio-btn play-mine"
              onClick={playMine}
              title="Play your recorded voice"
            >
              {isPlayingMine ? '⏸ Pause Mine' : '▶ Play Mine'}
            </button>
            <button
              className="instant-audio-btn play-target"
              onClick={() => speak(targetText)}
              title="Listen to native pronunciation"
            >
              🔊 Native
            </button>
            <button
              className="instant-audio-btn play-slow"
              onClick={() => speak(targetText, 0.6)}
              title="Listen slowly"
            >
              🐢 Slow
            </button>
            <button
              className="instant-audio-btn retry"
              onClick={startRecording}
              title="Record another attempt in 1 click"
            >
              🔄 Try Again
            </button>
          </div>
        )}
      </div>

      {speech.error && <p className="error small">{speech.error}</p>}
      {audio.error && <p className="error small">{audio.error}</p>}

      {audio.isRecording && speech.interimTranscript && (
        <p className="interim-text small" style={{ margin: '4px 0 0' }}>"{speech.interimTranscript}"</p>
      )}

      {scoring && (
        <p className="muted small" style={{ margin: '6px 0 0' }}>
          ⏳ Scoring with Whisper &amp; Wav2Vec2 Forced Alignment…
        </p>
      )}

      {/* Advanced Phoneme GOP & Whisper Scoring Results */}
      {!audio.isRecording && evalResult && (
        <div className="diff-panel-mini">
          <div className="diff-header-mini" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <span className="pill status-fixed" title="Whisper ASR word accuracy score">
                Whisper: {evalResult.simple.accuracy_score}%
              </span>
              <span className="pill status-practicing" title="Wav2Vec2 acoustic confidence (GOP score)">
                Acoustic GOP: {evalResult.advanced.overall_score}%
              </span>
            </div>
            {evalResult.simple.recognized_text && (
              <span className="muted small">
                Whisper heard: "{evalResult.simple.recognized_text}"
              </span>
            )}
          </div>

          {/* Phoneme Acoustic Confidence Cards */}
          <div className="gop-words-container">
            <p className="micro-kicker">
              Phoneme Acoustic Confidence (Click red sounds for tip):
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {evalResult.advanced.words.map((w, wi) => (
                <div key={wi} className={`gop-word-card ${w.is_mispronounced ? 'has-error' : ''}`}>
                  <div className="gop-word-label">
                    <strong>{w.word}</strong> <span className="muted small">{w.ipa}</span>
                  </div>
                  <div className="gop-phonemes-row">
                    {w.phonemes.map((ph, pi) => (
                      <span
                        key={pi}
                        className={`gop-ph-badge ${ph.is_mispronounced ? 'mispronounced' : 'accurate'}`}
                        title={ph.tip || `${ph.arpabet}: ${Math.round(ph.gop_score * 100)}% acoustic confidence`}
                        onClick={() => ph.tip && setActiveTip(activeTip === ph.tip ? null : ph.tip)}
                      >
                        {ph.ipa}
                        <span className="gop-score-val">{Math.round(ph.gop_score * 100)}%</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tip display if clicked */}
          {activeTip && (
            <div
              className="phoneme-tip-box banner info"
              style={{ margin: '6px 0 2px', padding: '6px 10px', fontSize: '12px' }}
            >
              💡 <b>Phonetic Tip:</b> {activeTip}
            </div>
          )}
        </div>
      )}

      {/* Fallback client-side live diff if Whisper/Wav2Vec2 is pending or unavailable */}
      {!audio.isRecording && !evalResult && diff && speech.transcript && (
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

function WordPracticeStrip({
  word,
  onClose,
}: {
  word: WordToken
  onClose: () => void
}) {
  return (
    <div className="word-practice-strip">
      <div className="word-practice-head">
        <div className="word-info">
          <span className="word-title">{word.text}</span>
          <span className="word-ipa">/{word.ipa}/</span>
          {word.syllables.length > 1 && (
            <span className="word-syllables">
              {word.spelling?.map((s, i) => (
                <span key={i} className={i === word.stressed_spelling ? 'stressed-syl' : ''}>
                  {i > 0 ? ' · ' : ''}
                  {i === word.stressed_spelling ? s.toUpperCase() : s}
                </span>
              ))}
            </span>
          )}
        </div>
        <div className="word-actions">
          <button className="icon" title="Listen (US voice)" onClick={() => speak(word.text)}>🔊</button>
          <button className="icon" title="Listen slowly" onClick={() => speak(word.text, 0.6)}>🐢</button>
          <button className="icon close" title="Close word practice" onClick={onClose}>✕</button>
        </div>
      </div>
      <ShadowingBox key={word.text} targetText={word.text} isWord />
    </div>
  )
}

function PartOverviewPanel({
  partIdx,
  totalParts,
  paras,
  vocabCount,
  pronCount,
  onSelectSentence,
}: {
  partIdx: number
  totalParts: number
  paras: Para[]
  vocabCount: number
  pronCount: number
  onSelectSentence: (text: string) => void
}) {
  const [showPartShadow, setShowPartShadow] = useState(false)
  const sentences = useMemo(() => {
    const list: string[] = []
    paras.forEach((p) => {
      const cleaned = cleanLineForIpa(p.text)
      if (cleaned) {
        list.push(cleaned)
      }
    })
    return list
  }, [paras])

  const wholePartText = useMemo(() => sentences.join(' '), [sentences])

  return (
    <div className="panel-inner part-overview-panel">
      <div className="part-overview-head">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="pill status-new">
            Part {partIdx + 1} of {totalParts}
          </span>
          <span className="muted small">
            {sentences.length} lines · {vocabCount} vocab · {pronCount} pron
          </span>
        </div>
        <h3 style={{ margin: '8px 0 4px', fontSize: '15px' }}>Whole Part Pronunciation &amp; Speaking</h3>
        <div className="part-audio-btns">
          <button
            className="primary"
            onClick={() => speak(wholePartText)}
            disabled={!wholePartText}
            title="Listen to the whole part at normal pace"
          >
            🔊 Listen Part
          </button>
          <button
            onClick={() => speak(wholePartText, 0.65)}
            disabled={!wholePartText}
            title="Listen to the whole part slowly"
          >
            🐢 Slow (0.65x)
          </button>
          <button
            className={`seg ${showPartShadow ? 'active' : ''}`}
            onClick={() => setShowPartShadow(!showPartShadow)}
            style={{ marginLeft: 'auto', fontSize: '11.5px', padding: '4px 10px' }}
          >
            {showPartShadow ? 'Hide Part Shadowing' : '🎙️ Shadow Part'}
          </button>
        </div>
      </div>

      {showPartShadow && wholePartText && (
        <ShadowingBox key={`part-${partIdx}`} targetText={wholePartText} isLine />
      )}

      <div className="part-sentences-box">
        <p className="micro-kicker" style={{ margin: '4px 0 6px' }}>
          Lines in this Part (Click to focus &amp; inspect):
        </p>
        <ul className="part-sentences-list">
          {sentences.map((sent, i) => (
            <li
              key={i}
              className="part-sentence-item"
              onClick={() => onSelectSentence(sent)}
            >
              <span className="muted small" style={{ minWidth: '18px' }}>
                {i + 1}.
              </span>
              <span className="sent-text" title={sent}>{sent}</span>
              <button
                className="icon"
                title="Listen sentence"
                onClick={(e) => {
                  e.stopPropagation()
                  speak(sent)
                }}
              >
                🔊
              </button>
            </li>
          ))}
        </ul>
      </div>

      <Legend />
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
  const [mode, setMode] = useState<'line' | 'side'>('line')
  const [qaViewMode, setQaViewMode] = useState<'practice' | 'transcript'>('practice')
  const [activeShadowLine, setActiveShadowLine] = useState<number | null>(null)
  const [activeWordPractice, setActiveWordPractice] = useState<{ lineIdx: number; word: WordToken } | null>(null)
  const [lineIpaCache, setLineIpaCache] = useState<Record<string, Token[]>>({})
  const [loadingLines, setLoadingLines] = useState(false)
  const [panel, setPanel] = useState<{ title: string; text: string; tokens: Token[]; item?: Item } | null>(null)

  useEffect(() => {
    setNote(null)
    setPartIdx(0)
    setPanel(null)
    setActiveShadowLine(null)
    setActiveWordPractice(null)
    api.note(id).then(setNote)
  }, [id])

  useEffect(() => {
    setActiveShadowLine(null)
    setActiveWordPractice(null)
  }, [partIdx])

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
                  const targetText = it?.text ?? s.text
                  if (mode === 'line') {
                    speak(targetText)
                  } else {
                    open(targetText, it)
                  }
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
              aria-pressed={mode === 'line'}
              onClick={() => setMode('line')}
            >
              Line-by-Line IPA
            </button>
            <button
              type="button"
              aria-pressed={mode === 'side'}
              onClick={() => setMode('side')}
            >
              Select &amp; Side Panel
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
                      {tokens && tokens.length > 0 && (
                        <Pronunciation
                          tokens={tokens}
                          onWordClick={(w) => {
                            speak(w.text)
                            setActiveWordPractice({ lineIdx: pi, word: w })
                          }}
                          activeWord={
                            activeWordPractice?.lineIdx === pi
                              ? activeWordPractice.word.text
                              : null
                          }
                        />
                      )}
                      {activeWordPractice?.lineIdx === pi && (
                        <WordPracticeStrip
                          word={activeWordPractice.word}
                          onClose={() => setActiveWordPractice(null)}
                        />
                      )}
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
                      <button
                        className="back-to-part-btn"
                        onClick={() => setPanel(null)}
                        title="Back to whole part overview"
                      >
                        ← Part Overview
                      </button>
                      <span className={`pill ${panel.item ? `kind-${panel.item.kind}` : ''}`}>{panel.title}</span>
                      <button className="icon" title="Listen (US voice)" onClick={() => speak(panel.text)}>🔊</button>
                      <button className="icon" title="Listen slowly" onClick={() => speak(panel.text, 0.6)}>🐢</button>
                      <button className="icon close" onClick={() => setPanel(null)}>✕</button>
                    </div>
                    <h3 style={{ margin: '8px 0 2px' }}>{panel.text}</h3>
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
                  <PartOverviewPanel
                    partIdx={safePartIdx}
                    totalParts={parts.length}
                    paras={currentParas}
                    vocabCount={partVocabCount}
                    pronCount={partPronCount}
                    onSelectSentence={(s) => open(s)}
                  />
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
