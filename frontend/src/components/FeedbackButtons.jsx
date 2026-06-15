import { useState } from 'react'
import { submitFeedback } from '../api'

export default function FeedbackButtons({ planId, itemType, itemName }) {
  const [rating, setRating] = useState(null)
  const [noteOpen, setNoteOpen] = useState(false)
  const [note, setNote] = useState('')
  const [noteSent, setNoteSent] = useState(false)

  async function handleRate(newRating) {
    setRating(newRating)
    try {
      await submitFeedback(planId, itemType, itemName, newRating)
    } catch {
      setRating(null)
    }
  }

  async function handleSendNote() {
    if (!note.trim() || !rating) return
    try {
      await submitFeedback(planId, itemType, itemName, rating, note.trim())
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
        className={`text-sm leading-none w-6 h-6 flex items-center justify-center rounded-full transition-colors ${
          rating === 'positive' ? 'bg-success-light opacity-100' : 'opacity-40 hover:opacity-70'
        }`}
      >
        👍
      </button>
      <button
        type="button"
        onClick={() => handleRate('negative')}
        title="Not for me"
        className={`text-sm leading-none w-6 h-6 flex items-center justify-center rounded-full transition-colors ${
          rating === 'negative' ? 'bg-danger-light opacity-100' : 'opacity-40 hover:opacity-70'
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
              className="text-xs border border-border rounded-lg px-1.5 py-0.5 w-28 focus:outline-none focus:ring-1 focus:ring-brand"
            />
            <button
              type="button"
              onClick={handleSendNote}
              className="text-xs text-brand hover:text-brand-dark font-semibold"
            >
              Send
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setNoteOpen(true)}
            className="text-xs text-ink-soft hover:text-ink"
          >
            + note
          </button>
        )
      )}
      {noteSent && <span className="text-xs text-ink-soft">Thanks!</span>}
    </div>
  )
}
