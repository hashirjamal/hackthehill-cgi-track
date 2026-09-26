import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layout/AppLayout'
import Accounts from './pages/Accounts'
import Backlog from './pages/Backlog'
import CaseDetail from './pages/CaseDetail'
import Cases from './pages/Cases'
import Classification from './pages/Classification'
import Profiles from './pages/Profiles'
import RootCause from './pages/RootCause'
import Simulator from './pages/Simulator'
import Worklist from './pages/Worklist'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/worklist" replace />} />
        <Route path="worklist" element={<Worklist />} />
        <Route path="cases" element={<Cases />} />
        <Route path="cases/:id" element={<CaseDetail />} />
        <Route path="backlog" element={<Backlog />} />
        <Route path="root-cause" element={<RootCause />} />
        <Route path="accounts" element={<Accounts />} />
        <Route path="profiles" element={<Profiles />} />
        <Route path="classification" element={<Classification />} />
        <Route path="simulator" element={<Simulator />} />
        <Route path="*" element={<Navigate to="/worklist" replace />} />
      </Route>
    </Routes>
  )
}
