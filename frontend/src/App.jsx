import { useState } from 'react'
import Chat from './components/Chat'

const PEOPLE = ['Chris', 'Kaitlyn']

export default function App() {
  const [person, setPerson] = useState('Chris')

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold text-sm">
            F
          </div>
          <span className="font-semibold text-gray-800">Franky Fitness</span>
        </div>

        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {PEOPLE.map(p => (
            <button
              key={p}
              onClick={() => setPerson(p)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                person === p
                  ? 'bg-white text-gray-800 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </header>

      <Chat key={person} person={person} />
    </div>
  )
}
