import { useEffect, useState } from 'react'
import { getCurrentUser, logout } from './api'
import AuthPage from './components/AuthPage'
import Chat from './components/Chat'
import ProfilePage from './components/ProfilePage'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('chat')

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .finally(() => setLoading(false))
  }, [])

  async function handleLogout() {
    await logout()
    setUser(null)
    setView('chat')
  }

  if (loading) {
    return <div className="flex items-center justify-center h-screen bg-gray-50 text-sm text-gray-400">Loading…</div>
  }

  if (!user) {
    return <AuthPage onAuth={setUser} />
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-sm">
            F
          </div>
          <span className="font-semibold text-gray-800">Franky Fitness</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setView('chat')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'chat' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setView('profile')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                view === 'profile' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Profile
            </button>
          </div>
          <span className="text-sm text-gray-600">{user.name}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-400 hover:text-gray-600"
          >
            Log out
          </button>
        </div>
      </header>

      {view === 'chat' ? <Chat user={user} /> : <ProfilePage />}
    </div>
  )
}
