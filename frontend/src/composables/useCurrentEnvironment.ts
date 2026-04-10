import { ref, computed, watch } from 'vue'
import { getEnvironments } from '@/api/environment'

const LS_KEY = 'current_test_environment_id'

export interface TestEnvironmentOption {
  id: number
  name: string
  base_url?: string
  env_type?: string
}

const environmentId = ref<number | null>(null)
const environments = ref<TestEnvironmentOption[]>([])

function normalizeId(raw: unknown): number | null {
  if (raw == null || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

function readStoredId(): number | null {
  const raw = localStorage.getItem(LS_KEY)
  return normalizeId(raw)
}

environmentId.value = readStoredId()

watch(
  environmentId,
  (v) => {
    if (v != null) {
      localStorage.setItem(LS_KEY, String(v))
    } else {
      localStorage.removeItem(LS_KEY)
    }
    window.dispatchEvent(
      new CustomEvent('app:current-environment-changed', {
        detail: { environmentId: v },
      }),
    )
  },
  { flush: 'post' },
)

export function useCurrentEnvironment() {
  const selectedEnvironment = computed(
    () => environments.value.find((e) => e.id === environmentId.value) ?? null,
  )
  const baseUrl = computed(() => (selectedEnvironment.value?.base_url || '').trim())

  async function loadEnvironments() {
    try {
      const { data } = await getEnvironments({ page_size: 500 })
      const list = Array.isArray(data?.results)
        ? data.results
        : Array.isArray(data)
          ? data
          : []
      environments.value = list
        .map((item) => {
          const id = normalizeId((item as { id?: unknown })?.id)
          if (id == null) return null
          return {
            ...(item as Omit<TestEnvironmentOption, 'id'>),
            id,
          } as TestEnvironmentOption
        })
        .filter((item): item is TestEnvironmentOption => item != null)
      const exists = environments.value.some((e) => e.id === environmentId.value)
      if (!exists && environmentId.value != null) {
        environmentId.value = null
      }
    } catch {
      environments.value = []
    }
  }

  function setEnvironmentId(id: number | string | null) {
    environmentId.value = normalizeId(id)
  }

  return {
    environmentId,
    environments,
    selectedEnvironment,
    baseUrl,
    loadEnvironments,
    setEnvironmentId,
  }
}
