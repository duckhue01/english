import { NavLink, Route, Routes } from 'react-router-dom'
import AnalyzerPage from './pages/AnalyzerPage'
import FoldersPage from './pages/FoldersPage'
import ItemsPage from './pages/ItemsPage'
import { NotesList, NoteView } from './pages/NotesPage'

export default function App() {
  return (
    <div className="app">
      <aside className="wip-banner" aria-label="Marking syntax notice">
        <div>
          <strong>American English Coach</strong>
          <span>
            Apple Notes rules: <b>Bold</b> → New Vocabulary · <u>Underline</u> → Pronunciation
          </span>
        </div>
      </aside>
      <header className="site-header">
        <NavLink to="/" className="brand" end>
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
          </span>
          notes<span>.coach</span>
        </NavLink>
        <nav aria-label="Primary navigation">
          <NavLink to="/" end>Folders</NavLink>
          <NavLink to="/vocab">Vocabulary</NavLink>
          <NavLink to="/pronunciation">Pronunciation</NavLink>
          <NavLink to="/notes">Notes</NavLink>
          <NavLink to="/analyze">Analyzer</NavLink>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<FoldersPage />} />
          <Route path="/vocab" element={<ItemsPage key="vocab" kind="vocab" />} />
          <Route path="/pronunciation" element={<ItemsPage key="pronunciation" kind="mistake" />} />
          <Route path="/mistakes" element={<ItemsPage key="mistake" kind="mistake" />} />
          <Route path="/notes" element={<NotesList />} />
          <Route path="/notes/:id" element={<NoteView />} />
          <Route path="/analyze" element={<AnalyzerPage />} />
        </Routes>
      </main>
    </div>
  )
}
