import { useState } from 'react'
import { savePlan } from '../api'

export default function WorkoutPlanCard({ plan, person }) {
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      await savePlan(person, plan, 'workout_plan')
      setSaved(true)
    } catch (e) {
      setError('Failed to save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <div className="flex items-center justify-between px-4 py-3 bg-blue-50 border-b border-gray-200">
        <span className="font-semibold text-blue-800 text-sm">Workout Plan</span>
        {!saved ? (
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving…' : 'Save Plan'}
          </button>
        ) : (
          <span className="text-xs text-blue-700 font-medium">Saved</span>
        )}
      </div>

      {error && <p className="text-xs text-red-600 px-4 py-2">{error}</p>}

      <div className="divide-y divide-gray-100">
        {plan.workout_days.map((day, i) => (
          <div key={i} className="px-4 py-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-medium text-gray-800 text-sm">{day.day}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">{day.focus}</span>
            </div>
            <ul className="text-sm text-gray-700 space-y-1">
              {day.exercises.map((ex, j) => (
                <li key={j} className="flex justify-between gap-4">
                  <span>{ex.exercise_name}</span>
                  <span className="text-gray-500 shrink-0">{ex.sets} × {ex.reps} · rest {ex.rest_seconds}s</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {plan.rest_days?.length > 0 && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 text-xs text-gray-500">
          Rest days: {plan.rest_days.join(', ')}
        </div>
      )}

      {plan.notes && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-500 italic">{plan.notes}</p>
        </div>
      )}
    </div>
  )
}
