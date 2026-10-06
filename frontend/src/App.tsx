import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import CompaniesPage from './pages/CompaniesPage'
import CompanyDetailPage from './pages/CompanyDetailPage'
import Dashboard from './pages/Dashboard'
import GraphPage from './pages/GraphPage'
import PersonsPage from './pages/PersonsPage'
import WarmIntroPage from './pages/WarmIntroPage'
import WarmupPage from './pages/WarmupPage'
import MailboxDetailPage from './pages/MailboxDetailPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/companies/:domain" element={<CompanyDetailPage />} />
        <Route path="/persons" element={<PersonsPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/warm-intro" element={<WarmIntroPage />} />
        <Route path="/warmup" element={<WarmupPage />} />
        <Route path="/warmup/:id" element={<MailboxDetailPage />} />
      </Route>
    </Routes>
  )
}
