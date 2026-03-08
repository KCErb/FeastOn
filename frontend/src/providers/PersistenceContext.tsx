/**
 * Persistence Provider Context
 *
 * Provides access to the persistence layer for the frontend.
 * Start with localStorage, can swap for IndexedDB or API later.
 */

import { createContext, useContext, ReactNode } from 'react'

interface PersistenceProvider {
  save: (collection: string, id: string, data: any) => Promise<void>
  load: (collection: string, id: string) => Promise<any | null>
  query: (collection: string, filter: Record<string, any>) => Promise<any[]>
  delete: (collection: string, id: string) => Promise<void>
}

class LocalStoragePersistence implements PersistenceProvider {
  private getKey(collection: string, id: string): string {
    return `conflang:${collection}:${id}`
  }

  async save(collection: string, id: string, data: any): Promise<void> {
    const key = this.getKey(collection, id)
    localStorage.setItem(key, JSON.stringify(data))
  }

  async load(collection: string, id: string): Promise<any | null> {
    const key = this.getKey(collection, id)
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  }

  async query(collection: string, filter: Record<string, any>): Promise<any[]> {
    const results: any[] = []
    const prefix = `conflang:${collection}:`

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key?.startsWith(prefix)) {
        const raw = localStorage.getItem(key)
        if (raw) {
          const data = JSON.parse(raw)
          // Simple filter: check if all filter key-value pairs match
          if (Object.entries(filter).every(([k, v]) => data[k] === v)) {
            results.push(data)
          }
        }
      }
    }

    return results
  }

  async delete(collection: string, id: string): Promise<void> {
    const key = this.getKey(collection, id)
    localStorage.removeItem(key)
  }
}

const PersistenceContext = createContext<PersistenceProvider | null>(null)

export function PersistenceProviderComponent({ children }: { children: ReactNode }) {
  const provider = new LocalStoragePersistence()

  return (
    <PersistenceContext.Provider value={provider}>
      {children}
    </PersistenceContext.Provider>
  )
}

export function usePersistence(): PersistenceProvider {
  const context = useContext(PersistenceContext)
  if (!context) {
    throw new Error('usePersistence must be used within PersistenceProviderComponent')
  }
  return context
}
