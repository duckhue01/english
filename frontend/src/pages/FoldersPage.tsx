import { useCallback, useEffect, useState } from 'react'
import { api, type AppleFolder, type AppStatus, type Folder, type SyncReport } from '../api'

function fmt(ts: string | null) {
  return ts ? new Date(ts).toLocaleString() : 'never'
}

export default function FoldersPage() {
  const [status, setStatus] = useState<AppStatus | null>(null)
  const [folders, setFolders] = useState<Folder[]>([])
  const [apple, setApple] = useState<AppleFolder[]>([])
  const [name, setName] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [report, setReport] = useState<SyncReport | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api.folders().then(setFolders)
    api.status().then(setStatus)
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

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Folders</h1>
          <p className="muted">Choose which Apple Notes folders to learn from. Apple Notes is only read, never changed.</p>
        </div>
        <button className="primary" disabled={!!busy || !folders.length}
          onClick={() => run('all', async () => setReport(await api.sync()))}>
          {busy === 'all' ? 'Syncing…' : '⟳ Sync all'}
        </button>
      </div>

      {status && !status.full_disk_access && (
        <div className="banner warn">
          <b>Highlights (vocabulary) are not readable yet.</b> AppleScript can see underlines but drops
          highlights, so the app has to read the Notes database directly. To allow that:
          <ol>
            <li>Open <b>System Settings → Privacy &amp; Security → Full Disk Access</b>.</li>
            <li>Turn it on for the app that runs the server (your terminal, e.g. Terminal, iTerm or Orca).</li>
            <li>Restart that app and run <code>./run.sh</code> again.</li>
          </ol>
        </div>
      )}
      {status?.full_disk_access && (
        <div className="banner ok">Reading the Notes database directly: highlights and underlines are both supported.</div>
      )}

      <div className="add-row">
        <input list="apple-folders" placeholder="Apple Notes folder name…" value={name}
          onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} />
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
              <b>{f.folder}</b> {f.notes} notes · {f.vocab} vocab · {f.mistake} mistakes
              {f.new_items ? ` · ${f.new_items} new` : ''}
            </span>
          ))}
        </div>
      )}

      {folders.length === 0 ? (
        <div className="empty"><p>No folders yet. Add one above, for example <i>Economic Crash Course</i>.</p></div>
      ) : (
        <table className="table">
          <thead>
            <tr><th>Folder</th><th>Notes</th><th>Vocab</th><th>Mistakes</th><th>Last synced</th><th /></tr>
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
                  <button className="danger" disabled={!!busy}
                    onClick={() => confirm(`Stop tracking "${f.name}"? Your statuses and comments are kept.`) &&
                      run('rm', () => api.removeFolder(f.name))}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
