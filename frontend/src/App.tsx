import { NavLink, Route, Routes } from 'react-router-dom'
import AnalyzerPage from './pages/AnalyzerPage'
import FoldersPage from './pages/FoldersPage'
import ItemsPage from './pages/ItemsPage'
import { NotesList, NoteView } from './pages/NotesPage'

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="brand">
          <span className="logo">Aa</span>
          <div>
            <b>Notes Coach</b>
            <small>American English</small>
          </div>
        </div>
        <NavLink to="/" end>📁 Folders</NavLink>
        <NavLink to="/vocab">🖍️ Vocabulary</NavLink>
        <NavLink to="/mistakes">🎯 Mistakes</NavLink>
        <NavLink to="/notes">📝 Notes</NavLink>
        <NavLink to="/analyze">🔬 Analyzer</NavLink>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<FoldersPage />} />
          <Route path="/vocab" element={<ItemsPage key="vocab" kind="vocab" />} />
          <Route path="/mistakes" element={<ItemsPage key="mistake" kind="mistake" />} />
          <Route path="/notes" element={<NotesList />} />
          <Route path="/notes/:id" element={<NoteView />} />
          <Route path="/analyze" element={<AnalyzerPage />} />
        </Routes>
      </main>
    </div>
  )
}
