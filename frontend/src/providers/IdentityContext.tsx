/**
 * Identity Provider Context
 *
 * Manages current user and preferences.
 * Stub implementation for now (no auth).
 */

import { createContext, useContext, ReactNode, useState } from 'react'

interface User {
  id: string
  displayName: string
}

interface UserPreferences {
  userId: string
  homeLanguage: string
  studyLanguages: string[]
  activeStudyLang: string
  playbackSpeed: number
  interlinearPauseMs: number
  showPhonetics: boolean
  showDiffMarkers: boolean
  fontSize: string
  theme: string
}

interface IdentityProvider {
  currentUser: User | null
  preferences: UserPreferences
  updatePreferences: (updates: Partial<UserPreferences>) => Promise<void>
}

const defaultPreferences: UserPreferences = {
  userId: 'default-user',
  homeLanguage: 'eng',
  studyLanguages: ['ces'],
  activeStudyLang: 'ces',
  playbackSpeed: 1.0,
  interlinearPauseMs: 500,
  showPhonetics: true,
  showDiffMarkers: true,
  fontSize: 'medium',
  theme: 'light',
}

const IdentityContext = createContext<IdentityProvider | null>(null)

export function IdentityProviderComponent({ children }: { children: ReactNode }) {
  const [currentUser] = useState<User>({
    id: 'default-user',
    displayName: 'Test User',
  })

  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)

  const updatePreferences = async (updates: Partial<UserPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...updates }))
  }

  return (
    <IdentityContext.Provider
      value={{
        currentUser,
        preferences,
        updatePreferences,
      }}
    >
      {children}
    </IdentityContext.Provider>
  )
}

export function useIdentity(): IdentityProvider {
  const context = useContext(IdentityContext)
  if (!context) {
    throw new Error('useIdentity must be used within IdentityProviderComponent')
  }
  return context
}
