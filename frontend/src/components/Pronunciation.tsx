import { Fragment } from 'react'
import type { Syllable, Token, WordToken } from '../api'

const FEATURE_TITLE: Record<string, string> = {
  flap: 'Flap T: a quick tap, like a soft "d" (water → wa-der)',
  glottal: 'Glottal T: stop the air in your throat (button → bu-ʔn)',
  t_drop: 'T often dropped after n in casual speech (twenty → twen-y)',
  coalesce: 'Sounds merge: t+y → ch, d+y → j (did you → di-jou)',
}

function SyllableView({ s, multi }: { s: Syllable; multi: boolean }) {
  const parts = s.ipa.split(/(ɾ|ʔ|\(t\))/).filter(Boolean)
  const cls = ['syl', multi && s.stress === 1 ? 'primary' : '', multi && s.stress === 2 ? 'secondary' : '']
  return (
    <span className={cls.join(' ')}>
      {multi && s.stress === 1 && <span className="stress-mark">ˈ</span>}
      {multi && s.stress === 2 && <span className="stress-mark">ˌ</span>}
      {parts.map((p, i) => {
        if (p === 'ɾ') return <span key={i} className="flap" title={FEATURE_TITLE.flap}>ɾ</span>
        if (p === 'ʔ') return <span key={i} className="glottal" title={FEATURE_TITLE.glottal}>ʔ</span>
        if (p === '(t)') return <span key={i} className="tdrop" title={FEATURE_TITLE.t_drop}>(t)</span>
        const coal = s.features.includes('coalesce') && /tʃ|dʒ|ʃ|ʒ/.test(p)
        return (
          <span key={i} className={coal ? 'coalesce' : undefined} title={coal ? FEATURE_TITLE.coalesce : undefined}>
            {p}
          </span>
        )
      })}
    </span>
  )
}

function WordView({
  w,
  onClick,
  isActive,
}: {
  w: WordToken
  onClick?: () => void
  isActive?: boolean
}) {
  const multi = w.syllables.length > 1
  const cls = [
    'word',
    w.weak ? 'weak' : '',
    onClick ? 'interactive' : '',
    isActive ? 'active-word' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span
      className={cls}
      onClick={onClick}
      title={
        onClick
          ? `Click to listen & practice word "${w.text}"`
          : w.weak
          ? 'Weak form: unstressed and reduced'
          : undefined
      }
    >
      <span className="spelling">
        {w.spelling
          ? w.spelling.map((s, i) => (
              <Fragment key={i}>
                {i > 0 && <span className="dot">·</span>}
                <span className={i === w.stressed_spelling ? 'stressed' : undefined}>
                  {i === w.stressed_spelling ? s.toUpperCase() : s}
                </span>
              </Fragment>
            ))
          : w.text}
      </span>
      <span className="ipa">
        {w.syllables.length === 0 ? '?' : null}
        {w.syllables.map((s, i) => (
          <Fragment key={i}>
            {i > 0 && s.stress === 0 && <span className="syl-sep">.</span>}
            <SyllableView s={s} multi={multi} />
          </Fragment>
        ))}
      </span>
      {w.source !== 'cmu' && (
        <span className="src" title={w.source === 'g2p' ? 'Not in dictionary: predicted pronunciation' : 'Unknown word'}>
          {w.source === 'g2p' ? 'predicted' : 'unknown'}
        </span>
      )}
    </span>
  )
}

function LinkView({ w }: { w: WordToken }) {
  const l = w.link_next
  if (!l) return <span className="gap" />
  return (
    <span className={`link link-${l.type}`} title={l.label}>
      ‿{l.insert && <sup>{l.insert}</sup>}
    </span>
  )
}

export function connectedIpa(tokens: Token[]): string {
  let out = ''
  tokens.forEach((t) => {
    if (!t.is_word) return
    out += t.ipa
    if (t.link_next) out += '‿' + (t.link_next.insert ?? '')
    else out += ' '
  })
  return out.trim()
}

export default function Pronunciation({
  tokens,
  compact = false,
  onWordClick,
  activeWord,
}: {
  tokens: Token[]
  compact?: boolean
  onWordClick?: (word: WordToken) => void
  activeWord?: string | null
}) {
  const words = tokens.filter((t): t is WordToken => t.is_word)
  if (!words.length) return null
  return (
    <div className={`pron ${compact ? 'compact' : ''}`}>
      <div className="pron-words">
        {tokens.map((t, i) =>
          t.is_word ? (
            <Fragment key={i}>
              <WordView
                w={t}
                onClick={onWordClick ? () => onWordClick(t) : undefined}
                isActive={activeWord === t.text}
              />
              <LinkView w={t} />
            </Fragment>
          ) : (
            <span key={i} className="punct">{t.text}</span>
          ),
        )}
      </div>
      {!compact && <div className="connected">/{connectedIpa(tokens)}/</div>}
    </div>
  )
}

export function Legend() {
  return (
    <div className="legend">
      <span><b className="primary-demo">ˈSYL</b> primary stress</span>
      <span><b className="secondary-demo">ˌsyl</b> secondary stress</span>
      <span><b className="flap">ɾ</b> flap T</span>
      <span><b className="glottal">ʔ</b> glottal T</span>
      <span><b className="tdrop">(t)</b> T can drop</span>
      <span><b className="link link-cv">‿</b> consonant → vowel</span>
      <span><b className="link link-glide_j">‿<sup>j</sup></b><b className="link link-glide_w">‿<sup>w</sup></b> glide</span>
      <span><b className="link link-same">‿</b> same / held sound</span>
      <span><b className="coalesce">tʃ dʒ</b> sounds merge</span>
      <span><i className="weak-demo">weak</i> reduced function word</span>
    </div>
  )
}
