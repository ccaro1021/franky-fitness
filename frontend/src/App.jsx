import { useEffect, useState } from 'react'
import { getCurrentUser, logout } from './api'
import AuthPage from './components/AuthPage'
import Chat from './components/Chat'
import ProfilePage from './components/ProfilePage'
import SavedItemsPage from './components/SavedItemsPage'

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
    return (
      <div className="flex items-center justify-center h-screen bg-bg text-sm text-ink-soft">
        Loading…
      </div>
    )
  }

  if (!user) {
    return <AuthPage onAuth={setUser} />
  }

  return (
    <div className="flex flex-col h-screen bg-bg">
      <header className="bg-brand px-4 py-3 flex items-center justify-between shrink-0 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-white flex items-center justify-center text-brand font-display font-extrabold text-base shadow-sm">
            F
          </div>
          <span className="font-display font-bold text-white text-lg tracking-tight">Franky Fitness</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 bg-white/15 rounded-full p-1">
            <button
              onClick={() => setView('chat')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                view === 'chat' ? 'bg-white text-brand shadow-sm' : 'text-white/80 hover:text-white'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setView('saved')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                view === 'saved' ? 'bg-white text-brand shadow-sm' : 'text-white/80 hover:text-white'
              }`}
            >
              Saved
            </button>
            <button
              onClick={() => setView('profile')}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                view === 'profile' ? 'bg-white text-brand shadow-sm' : 'text-white/80 hover:text-white'
              }`}
            >
              Profile
            </button>
          </div>
          <span className="text-sm text-white font-medium hidden sm:inline">{user.name}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-white/70 hover:text-white transition-colors"
          >
            Log out
          </button>
        </div>
      </header>

      {view === 'chat' && <Chat user={user} />}
      {view === 'saved' && <SavedItemsPage />}
      {view === 'profile' && <ProfilePage />}
    </div>
  )
}
