import { useState } from 'react'
import { api, speak, type Token } from '../api'
import Pronunciation, { Legend } from '../components/Pronunciation'

const EXAMPLES = [
  'Economics is the study of scarcity and choices.',
  'What about it? I got a lot of water.',
  'Did you want to go away for a bit?',
  'Pronunciation is better if you practice twenty minutes a day.',
]

export default function AnalyzerPage() {
  const [text, setText] = useState(EXAMPLES[0])
  const [tokens, setTokens] = useState<Token[] | null>(null)
  const [loading, setLoading] = useState(false)

  const run = async (t = text) => {
    setLoading(true)
    try {
      setTokens(await api.analyze(t))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <div className="page-head">
        <div>
          <p className="section-kicker">General American Phonetics</p>
          <h1>Analyzer</h1>
          <p className="muted">Paste any English text to see American IPA, syllable stress, linking and flap-T.</p>
        </div>
      </div>
      <textarea className="big-input" rows={3} value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => (e.metaKey || e.ctrlKey) && e.key === 'Enter' && run()} />
      <div className="row">
        <button className="primary" onClick={() => run()} disabled={loading}>{loading ? 'Analyzing…' : 'Analyze (⌘↵)'}</button>
        <button onClick={() => speak(text)}>🔊 Listen</button>
        <button onClick={() => speak(text, 0.6)}>🐢 Slow</button>
        <span className="spacer" />
        {EXAMPLES.map((ex) => (
          <button key={ex} className="chip" onClick={() => { setText(ex); run(ex) }}>{ex.slice(0, 22)}…</button>
        ))}
      </div>
      <Legend />
      {tokens && <div className="card"><Pronunciation tokens={tokens} /></div>}
    </section>
  )
}
