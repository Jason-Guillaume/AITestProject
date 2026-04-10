import { defineStore } from 'pinia'

const CURRENT_PROJECT_LS = 'current_project_id'
const CURRENT_ENVIRONMENT_LS = 'current_test_environment_id'

function parseStorageId(key) {
  const raw = localStorage.getItem(key)
  if (raw == null || raw === '') return null
  return String(raw)
}

export const useAppContextStore = defineStore('appContext', {
  state: () => ({
    state: {
      activeProject: {
        id: parseStorageId(CURRENT_PROJECT_LS),
        name: '',
      },
      activeEnvironment: {
        id: parseStorageId(CURRENT_ENVIRONMENT_LS),
        name: '',
      },
    },
  }),
  actions: {
    setActiveProject(project) {
      this.state.activeProject.id = project?.id == null || project?.id === '' ? null : String(project.id)
      this.state.activeProject.name = project?.name ? String(project.name) : ''
      if (this.state.activeProject.id != null) {
        localStorage.setItem(CURRENT_PROJECT_LS, String(this.state.activeProject.id))
      } else {
        localStorage.removeItem(CURRENT_PROJECT_LS)
      }
      window.dispatchEvent(
        new CustomEvent('app:current-project-changed', {
          detail: {
            projectId: this.state.activeProject.id,
            projectName: this.state.activeProject.name,
          },
        }),
      )
    },
    setActiveEnvironment(environment) {
      this.state.activeEnvironment.id = environment?.id == null || environment?.id === '' ? null : String(environment.id)
      this.state.activeEnvironment.name = environment?.name ? String(environment.name) : ''
      if (this.state.activeEnvironment.id != null) {
        localStorage.setItem(CURRENT_ENVIRONMENT_LS, String(this.state.activeEnvironment.id))
      } else {
        localStorage.removeItem(CURRENT_ENVIRONMENT_LS)
      }
      window.dispatchEvent(
        new CustomEvent('app:current-environment-changed', {
          detail: {
            environmentId: this.state.activeEnvironment.id,
            environmentName: this.state.activeEnvironment.name,
          },
        }),
      )
    },
  },
})
