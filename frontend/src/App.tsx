import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ProjectProvider } from './context/ProjectContext'
import { Loader2 } from 'lucide-react'
import Layout from './components/Layout'
import WelcomeScreen from './components/WelcomeScreen'
import UpgradeModal from './components/UpgradeModal'
import Dashboard from './pages/Dashboard'
import QA from './pages/QA'
import Upload from './pages/Upload'
import Projects from './pages/Projects'
import Flood from './pages/Flood'
import Review from './pages/Review'
import ISO from './pages/ISO'
import CAD from './pages/CAD'
import Agent from './pages/Agent'
import ProjectList from './pages/workspace/ProjectList'
import ProjectWorkspace from './pages/workspace/ProjectWorkspace'

function AppContent() {
  const { user, isLoading, showUpgrade, closeUpgrade, upgradeReason } = useAuth()

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-neutral-50">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
      </div>
    )
  }

  if (!user) {
    return (
      <>
        <WelcomeScreen />
        <UpgradeModal isOpen={showUpgrade} onClose={closeUpgrade} reason={upgradeReason} />
      </>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/workspace" replace />} />
        <Route path="/workspace" element={<ProjectList />} />
        <Route path="/workspace/:projectId" element={<ProjectWorkspace />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/qa" element={<QA />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/flood" element={<Flood />} />
        <Route path="/review" element={<Review />} />
        <Route path="/iso" element={<ISO />} />
        <Route path="/cad" element={<CAD />} />
      </Routes>
      <UpgradeModal isOpen={showUpgrade} onClose={closeUpgrade} reason={upgradeReason} />
    </Layout>
  )
}

function App() {
  return (
    <AuthProvider>
      <ProjectProvider>
        <AppContent />
      </ProjectProvider>
    </AuthProvider>
  )
}

export default App
