import ChatPanel from '../components/ChatPanel'

export default function ChatFullScreen() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex justify-center">
      <div className="w-full max-w-3xl h-screen flex flex-col p-4">
        <div className="flex items-baseline justify-between gap-3">
          <h1 className="text-xl font-bold">Ask the data</h1>
          <a href="/" className="text-xs text-indigo-400 hover:text-indigo-300">
            ← Back to rankings
          </a>
        </div>
        <p className="text-sm text-gray-500 mt-1 mb-4 leading-relaxed">
          Ask about any player or metric in the database. I can rank, filter and compare.
        </p>
        <ChatPanel fullScreen />
      </div>
    </div>
  )
}
