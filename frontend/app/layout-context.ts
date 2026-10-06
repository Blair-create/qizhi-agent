'use client'

import { createContext, useContext } from 'react'

type LayoutContextType = {
  agentId: string
  setAgentId: (agentId: string) => void
  currentThreadId: string | null
  setCurrentThreadId: (currentThreadId: string | null) => void
}

export const LayoutContext = createContext<LayoutContextType | null>(null)

export function useLayoutContext() {
  const context = useContext(LayoutContext)
  if (!context) {
    throw new Error('useLayoutContext 必须在 LayoutProvider 内部使用')
  }
  return context
}
