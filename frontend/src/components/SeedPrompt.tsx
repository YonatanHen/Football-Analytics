import type { ReactNode } from 'react'

export default function SeedPrompt() {
  return (
    <Center>
      <div className="text-5xl mb-4">⚽</div>
      <h2 className="text-xl font-bold text-gray-100 mb-3">No player data loaded</h2>
      <p className="text-gray-400 text-sm max-w-md text-center leading-relaxed">
        Data loading is now developer-driven via the <code className="text-gray-300">fetch_cli</code> tool.
        Run it from <code className="text-gray-300">tools/fetch_cli</code> (see its README), then refresh
        this page.
      </p>
    </Center>
  )
}

function Center({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      {children}
    </div>
  )
}
