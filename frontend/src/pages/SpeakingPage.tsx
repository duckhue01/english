import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  speak,
  type Folder,
  type QAItem,
  type QAEvalResult,
  type ShadowingSentence,
} from '../api'
import Pronunciation from '../components/Pronunciation'
import { diffWords, useAudioRecorder, useSpeechRecognition } from '../speech'

type TabMode = 'shadowing' | 'qa'

export default function SpeakingPage() {
  const [mode, setMode] = useState<TabMode>('shadowing')
  const [folders, setFolders] = useState<Folder[]>([])
  const [folder, setFolder] = useState('')

  // Shadowing state
  const [sentences, setSentences] = useState<ShadowingSentence[] | null>(null)
  const [sentIdx, setSentIdx] = useState(0)

  // QA state
  const [qaList, setQaList] = useState<QAItem[] | null>(null)
  const [qaIdx, setQaIdx] = useState(0)
  const [qaEval, setQaEval] = useState<QAEvalResult | null>(null)
  const [evaluating, setEvaluating] = useState(false)
  const [showModelAnswer, setShowModelAnswer] = useState(false)

  // Audio & Speech hooks for Shadowing
  const shadowSpeech = useSpeechRecognition()
  const shadowAudio = useAudioRecorder()

  // Audio & Speech hooks for Q&A
  const qaSpeech = useSpeechRecognition()
  const qaAudio = useAudioRecorder()

  useEffect(() => {
    api.folders().then(setFolders).catch(() => {})
  }, [])

  // Load shadowing sentences
  useEffect(() => {
    setSentences(null)
    setSentIdx(0)
    api
      .speakingSentences({ folder: folder || undefined })
      .then((data) => setSentences(data))
      .catch(() => setSentences([]))
  }, [folder])

  // Load QA items
  useEffect(() => {
    setQaList(null)
    setQaIdx(0)
    setQaEval(null)
    setShowModelAnswer(false)
    api
      .speakingQA(folder || undefined)
      .then((data) => setQaList(data))
      .catch(() => setQaList([]))
  }, [folder])

  const currentSentence = sentences?.[sentIdx] ?? null
  const currentQA = qaList?.[qaIdx] ?? null

  // Shadowing diff calculation
  const shadowingDiff = useMemo(() => {
    if (!currentSentence || !shadowSpeech.transcript) return null
    return diffWords(currentSentence.text, shadowSpeech.transcript)
  }, [currentSentence, shadowSpeech.transcript])

  // Toggle Shadowing recording
  const handleToggleShadowing = async () => {
    if (shadowAudio.isRecording || shadowSpeech.isListening) {
      shadowAudio.stopRecording()
      shadowSpeech.stopListening()
    } else {
      shadowSpeech.resetTranscript()
      shadowAudio.resetAudio()
      await shadowAudio.startRecording()
      shadowSpeech.startListening()
    }
  }

  // Toggle QA recording
  const handleToggleQA = async () => {
    if (qaAudio.isRecording || qaSpeech.isListening) {
      qaAudio.stopRecording()
      qaSpeech.stopListening()

      // Submit for evaluation
      if (currentQA) {
        setEvaluating(true)
        try {
          const res = await api.evaluateAnswer({
            question: currentQA,
            spoken_text: qaSpeech.transcript || qaSpeech.interimTranscript || 'No speech detected',
            duration_sec: qaAudio.duration,
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
      setShowModelAnswer(false)
      qaSpeech.resetTranscript()
      qaAudio.resetAudio()
      await qaAudio.startRecording()
      qaSpeech.startListening()
    }
  }

  const nextSentence = () => {
    if (!sentences?.length) return
    shadowAudio.resetAudio()
    shadowSpeech.resetTranscript()
    setSentIdx((prev) => (prev + 1) % sentences.length)
  }

  const prevSentence = () => {
    if (!sentences?.length) return
    shadowAudio.resetAudio()
    shadowSpeech.resetTranscript()
    setSentIdx((prev) => (prev - 1 + sentences.length) % sentences.length)
  }

  const nextQA = () => {
    if (!qaList?.length) return
    qaAudio.resetAudio()
    qaSpeech.resetTranscript()
    setQaEval(null)
    setShowModelAnswer(false)
    setQaIdx((prev) => (prev + 1) % qaList.length)
  }

  const prevQA = () => {
    if (!qaList?.length) return
    qaAudio.resetAudio()
    qaSpeech.resetTranscript()
    setQaEval(null)
    setShowModelAnswer(false)
    setQaIdx((prev) => (prev - 1 + qaList.length) % qaList.length)
  }

  return (
    <section className="speaking-page">
      <div className="page-head">
        <div>
          <p className="section-kicker">Speaking & Oral Fluency Coach</p>
          <h1>Speaking Practice</h1>
          <p className="muted">
            Shadow native sentences with instant pronunciation diffing, and answer folder Questions & Answers with spoken concept feedback.
          </p>
        </div>

        <div className="segmented">
          <button
            className={`seg ${mode === 'shadowing' ? 'active' : ''}`}
            onClick={() => setMode('shadowing')}
          >
            🎙️ Shadowing ({sentences ? sentences.length : '…'})
          </button>
          <button
            className={`seg ${mode === 'qa' ? 'active' : ''}`}
            onClick={() => setMode('qa')}
          >
            💬 Questions & Answers ({qaList ? qaList.length : '…'})
          </button>
        </div>
      </div>

      {/* Filter Row */}
      <div className="filters">
        <select value={folder} onChange={(e) => setFolder(e.target.value)}>
          <option value="">All folders</option>
          {folders.map((f) => (
            <option key={f.name} value={f.name}>
              {f.name}
            </option>
          ))}
        </select>
        <span className="spacer" />
        <span className="muted" style={{ fontSize: '12px' }}>
          Tip: Chrome, Edge, or Safari gives optimal microphone speech recognition.
        </span>
      </div>

      {/* MODE 1: SHADOWING */}
      {mode === 'shadowing' && (
        <div className="speaking-container">
          {!sentences && <p className="muted">Loading practice sentences…</p>}
          {sentences && sentences.length === 0 && (
            <div className="empty">
              <p>No practice sentences found. Sync a folder with notes and vocabulary first.</p>
            </div>
          )}

          {currentSentence && (
            <div className="card speaking-card">
              <header className="card-head">
                <span className="pill status-new">
                  Sentence {sentIdx + 1} of {sentences?.length ?? 0}
                </span>
                {currentSentence.target_word && (
                  <span className={`pill kind-${currentSentence.kind}`}>
                    Focus: {currentSentence.target_word}
                  </span>
                )}
                <span className="spacer" />
                <Link
                  className="note-link"
                  to={`/notes/${encodeURIComponent(currentSentence.note_id)}`}
                >
                  {currentSentence.folder} › {currentSentence.note_title}
                </Link>
              </header>

              {/* Target Sentence Display */}
              <div className="speaking-target">
                <blockquote className="speaking-text">{currentSentence.text}</blockquote>
                <div className="audio-actions">
                  <button
                    className="primary"
                    onClick={() => speak(currentSentence.text)}
                    title="Listen at normal native pace"
                  >
                    🔊 Listen
                  </button>
                  <button
                    onClick={() => speak(currentSentence.text, 0.65)}
                    title="Listen slowly to hear phonetic reductions"
                  >
                    🐢 Slow (0.65x)
                  </button>
                </div>
              </div>

              {/* Phonetics analysis breakdown */}
              {currentSentence.tokens && currentSentence.tokens.length > 0 && (
                <div className="speaking-phonetics">
                  <p className="micro-kicker">Phonetic breakdown:</p>
                  <Pronunciation tokens={currentSentence.tokens} />
                </div>
              )}

              {/* Record / Speaking Section */}
              <div className="record-panel">
                <div className="record-controls">
                  <button
                    className={`record-btn ${shadowAudio.isRecording ? 'recording' : ''}`}
                    onClick={handleToggleShadowing}
                  >
                    {shadowAudio.isRecording ? '⏹ Stop Recording' : '🎙️ Record & Speak'}
                  </button>
                  {shadowAudio.isRecording && (
                    <span className="pulse-indicator">
                      <span className="pulse-dot" /> Recording… ({shadowAudio.duration}s)
                    </span>
                  )}
                  {shadowAudio.audioUrl && !shadowAudio.isRecording && (
                    <div className="audio-playback">
                      <span className="muted">Your voice:</span>
                      <audio controls src={shadowAudio.audioUrl} />
                    </div>
                  )}
                </div>

                {shadowSpeech.error && <p className="error">{shadowSpeech.error}</p>}
                {shadowAudio.error && <p className="error">{shadowAudio.error}</p>}

                {/* Spoken live interim feedback */}
                {shadowAudio.isRecording && shadowSpeech.interimTranscript && (
                  <p className="interim-text">"{shadowSpeech.interimTranscript}"</p>
                )}

                {/* Accuracy Diff Result */}
                {!shadowAudio.isRecording && shadowingDiff && shadowSpeech.transcript && (
                  <div className="diff-panel">
                    <div className="diff-header">
                      <span
                        className={`pill ${shadowingDiff.accuracy >= 80 ? 'status-fixed' : shadowingDiff.accuracy >= 50 ? 'status-practicing' : 'status-new'}`}
                        style={{ fontSize: '13px', padding: '4px 10px' }}
                      >
                        {shadowingDiff.accuracy}% Accuracy
                      </span>
                      <span className="muted">Word comparison:</span>
                    </div>

                    <div className="diff-words">
                      {shadowingDiff.diff.map((w, i) => (
                        <span key={i} className={`diff-word diff-${w.status}`}>
                          {w.text}{' '}
                        </span>
                      ))}
                    </div>

                    <p className="diff-legend muted">
                      <span className="diff-legend-item">
                        <span className="sample matched" /> Matched
                      </span>
                      <span className="diff-legend-item">
                        <span className="sample missed" /> Missed / Mispronounced
                      </span>
                      <span className="diff-legend-item">
                        <span className="sample extra" /> Extra word
                      </span>
                    </p>
                  </div>
                )}
              </div>

              {/* Card Footer Navigation */}
              <footer className="card-foot" style={{ justifyContent: 'space-between', display: 'flex' }}>
                <button onClick={prevSentence} disabled={sentIdx === 0}>
                  ← Previous
                </button>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => {
                      shadowAudio.resetAudio()
                      shadowSpeech.resetTranscript()
                    }}
                  >
                    Clear / Retry
                  </button>
                  <button
                    className="primary"
                    onClick={nextSentence}
                    disabled={!sentences || sentIdx >= sentences.length - 1}
                  >
                    Next Sentence →
                  </button>
                </div>
              </footer>
            </div>
          )}
        </div>
      )}

      {/* MODE 2: QUESTIONS & ANSWERS */}
      {mode === 'qa' && (
        <div className="speaking-container">
          {!qaList && <p className="muted">Loading folder Questions & Answers…</p>}
          {qaList && qaList.length === 0 && (
            <div className="empty">
              <p>No "Questions & Answers" note found in this folder. Make sure your folder includes a note with Questions and Key Points.</p>
            </div>
          )}

          {currentQA && (
            <div className="card speaking-card">
              <header className="card-head">
                <span className="pill status-practicing">
                  Question {qaIdx + 1} of {qaList?.length ?? 0}
                </span>
                <span className="pill" style={{ background: 'var(--paper-deep)' }}>
                  {currentQA.topic}
                </span>
                {currentQA.subtopic !== currentQA.topic && (
                  <span className="pill" style={{ background: 'var(--surface-blue)' }}>
                    {currentQA.subtopic}
                  </span>
                )}
                <span className="spacer" />
                <Link
                  className="note-link"
                  to={`/notes/${encodeURIComponent(currentQA.note_id)}`}
                >
                  {currentQA.folder} › {currentQA.note_title}
                </Link>
              </header>

              {/* Question prompt */}
              <div className="speaking-target">
                <p className="micro-kicker">Question Prompt:</p>
                <h2 className="qa-prompt">{currentQA.question}</h2>
                <div className="audio-actions">
                  <button
                    onClick={() => speak(currentQA.question)}
                    title="Listen to question spoken in US English"
                  >
                    🔊 Listen to Question
                  </button>
                </div>
              </div>

              {/* Spoken Answer Recording Box */}
              <div className="record-panel">
                <div className="record-controls">
                  <button
                    className={`record-btn ${qaAudio.isRecording ? 'recording' : ''}`}
                    onClick={handleToggleQA}
                    disabled={evaluating}
                  >
                    {evaluating
                      ? 'Analyzing speech…'
                      : qaAudio.isRecording
                      ? '⏹ Finish Answer & Evaluate'
                      : '🎙️ Record Spoken Answer'}
                  </button>

                  {qaAudio.isRecording && (
                    <span className="pulse-indicator">
                      <span className="pulse-dot" /> Speaking… ({qaAudio.duration}s)
                    </span>
                  )}

                  {qaAudio.audioUrl && !qaAudio.isRecording && (
                    <div className="audio-playback">
                      <span className="muted">Your answer recording:</span>
                      <audio controls src={qaAudio.audioUrl} />
                    </div>
                  )}
                </div>

                {qaSpeech.error && <p className="error">{qaSpeech.error}</p>}
                {qaAudio.error && <p className="error">{qaAudio.error}</p>}

                {/* Spoken live interim text while speaking */}
                {qaAudio.isRecording && (
                  <div className="transcript-live-box">
                    <p className="micro-kicker">Live Transcription:</p>
                    <p className="transcript-text">
                      {qaSpeech.transcript}{' '}
                      <span className="interim-text">{qaSpeech.interimTranscript}</span>
                    </p>
                  </div>
                )}

                {/* Spoken Answer Evaluation Feedback */}
                {!qaAudio.isRecording && qaEval && (
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

                    {/* What you said */}
                    <div className="transcript-spoken-box">
                      <p className="micro-kicker">Your Spoken Answer:</p>
                      <p className="transcript-text">"{qaEval.spoken_text}"</p>
                    </div>

                    {/* Concept coverage checklist */}
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

                {/* Model Key Points Reveal Toggle */}
                {!qaAudio.isRecording && (
                  <div style={{ marginTop: '1rem' }}>
                    <button
                      className="link-btn"
                      onClick={() => setShowModelAnswer(!showModelAnswer)}
                    >
                      {showModelAnswer ? '▼ Hide Key Points & Model Guide' : '▶ Reveal Key Points & Model Guide'}
                    </button>
                    {showModelAnswer && (
                      <div className="model-answer-box">
                        <h4 style={{ margin: '0 0 8px' }}>Target Concepts for this Question:</h4>
                        <ul className="model-points-list">
                          {currentQA.key_points.map((kp, i) => (
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

              {/* QA Navigation Footer */}
              <footer className="card-foot" style={{ justifyContent: 'space-between', display: 'flex' }}>
                <button onClick={prevQA} disabled={qaIdx === 0}>
                  ← Previous Question
                </button>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => {
                      qaAudio.resetAudio()
                      qaSpeech.resetTranscript()
                      setQaEval(null)
                    }}
                  >
                    Clear / Retry
                  </button>
                  <button
                    className="primary"
                    onClick={nextQA}
                    disabled={!qaList || qaIdx >= qaList.length - 1}
                  >
                    Next Question →
                  </button>
                </div>
              </footer>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
