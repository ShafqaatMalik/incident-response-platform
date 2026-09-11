import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { IncidentDetailPage } from './pages/IncidentDetailPage'
import { IncidentListPage } from './pages/IncidentListPage'

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<IncidentListPage />} />
        <Route path="/incidents/:id" element={<IncidentDetailPage />} />
      </Routes>
    </AppShell>
  )
}
