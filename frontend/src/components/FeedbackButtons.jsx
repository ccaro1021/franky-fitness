import { useState } from 'react'
import { submitFeedback } from '../api'

export default function FeedbackButtons({ person, planId, itemType, itemName }) {
  const [rating, setRating] = useState(null)
  const [noteOpen, setNoteOpen] = useState(false)
  const [note, setNote] = useState('')
  const [noteSent, setNoteSent] = useState(false)

  async function handleRate(newRating) {
    setRating(newRating)
    try {
      await submitFeedback(person, planId, itemType, itemName, newRating)
    } catch {
      setRating(null)
    }
  }

  async function handleSendNote() {
    if (!note.trim() || !rating) return
    try {
      await submitFeedback(person, planId, itemType, itemName, rating, note.trim())
      setNoteSent(true)
      setNoteOpen(false)
    } catch {
      // leave the note open so the user can retry
    }
  }

  return (
    <div className="inline-flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => handleRate('positive')}
        title="I like this"
        className={`text-sm leading-none px-1 py-0.5 rounded transition-colors ${
          rating === 'positive' ? 'opacity-100' : 'opacity-40 hover:opacity-70'
        }`}
      >
        👍
      </button>
      <button
        type="button"
        onClick={() => handleRate('negative')}
        title="Not for me"
        className={`text-sm leading-none px-1 py-0.5 rounded transition-colors ${
          rating === 'negative' ? 'opacity-100' : 'opacity-40 hover:opacity-70'
        }`}
      >
        👎
      </button>

      {rating && !noteSent && (
        noteOpen ? (
          <span className="inline-flex items-center gap-1">
            <input
              type="text"
              autoFocus
              value={note}
              onChange={e => setNote(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSendNote()}
              placeholder="Why? (optional)"
              className="text-xs border border-gray-200 rounded px-1.5 py-0.5 w-28 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <button
              type="button"
              onClick={handleSendNote}
              className="text-xs text-emerald-600 hover:text-emerald-700"
            >
              Send
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setNoteOpen(true)}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            + note
          </button>
        )
      )}
      {noteSent && <span className="text-xs text-gray-400">Thanks!</span>}
    </div>
  )
}
