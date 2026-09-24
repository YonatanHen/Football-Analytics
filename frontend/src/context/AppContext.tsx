import { createContext, useContext } from 'react'
import type { Meta } from '../api/meta'

export type Tab = 'players' | 'compare' | 'sleepers' | 'scatter' | 'chat'

export interface GoOptions { comparePlayerId?: string }

export interface AppState {
  season: string
  meta: Meta | null
  go: (tab: Tab, opts?: GoOptions) => void
}

export const AppContext = createContext<AppState>({ season: '', meta: null, go: () => {} })

export const useApp = () => useContext(AppContext)
