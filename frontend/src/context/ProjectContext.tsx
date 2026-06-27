import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { projectsApi, type Project, type ProjectDetail, type ProjectCreate } from '../api/projects'

interface ProjectContextType {
  // 当前项目
  currentProject: ProjectDetail | null
  setCurrentProject: (p: ProjectDetail | null) => void

  // 项目列表
  projects: Project[]
  loading: boolean
  error: string

  // 操作
  refreshProjects: () => Promise<void>
  createProject: (data: ProjectCreate) => Promise<ProjectDetail>
  updateProject: (id: number | string, data: Partial<ProjectCreate>) => Promise<void>
  deleteProject: (id: number | string) => Promise<void>
}

const ProjectContext = createContext<ProjectContextType | null>(null)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [currentProject, setCurrentProject] = useState<ProjectDetail | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const refreshProjects = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await projectsApi.list()
      setProjects(res.items)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '加载项目列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshProjects()
  }, [refreshProjects])

  const createProject = useCallback(async (data: ProjectCreate): Promise<Project> => {
    const result = await projectsApi.create(data)
    // 创建后刷新列表以获取完整项目对象
    await refreshProjects()
    // 找到新创建的项目并返回
    const newProject = await projectsApi.get(result.id)
    return newProject
  }, [refreshProjects])

  const updateProject = useCallback(async (id: number | string, data: Partial<ProjectCreate>) => {
    await projectsApi.update(id, data)
    // 更新后刷新列表
    await refreshProjects()
    // 如果是当前项目，也更新currentProject
    if (currentProject?.id === Number(id)) {
      const updated = await projectsApi.get(id)
      setCurrentProject(updated)
    }
  }, [currentProject, refreshProjects])

  const deleteProject = useCallback(async (id: number | string) => {
    await projectsApi.delete(id)
    setProjects(prev => prev.filter(p => p.id !== Number(id)))
    if (currentProject?.id === Number(id)) setCurrentProject(null)
    await refreshProjects()
  }, [currentProject, refreshProjects])

  return (
    <ProjectContext.Provider value={{
      currentProject,
      setCurrentProject,
      projects,
      loading,
      error,
      refreshProjects,
      createProject,
      updateProject,
      deleteProject,
    }}>
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  const ctx = useContext(ProjectContext)
  if (!ctx) throw new Error('useProject must be used within ProjectProvider')
  return ctx
}
