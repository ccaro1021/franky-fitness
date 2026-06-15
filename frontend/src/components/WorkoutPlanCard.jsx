import { useState } from 'react'
import { savePlan } from '../api'
import FeedbackButtons from './FeedbackButtons'

export default function WorkoutPlanCard({ plan }) {
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [planId, setPlanId] = useState(null)

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const { id } = await savePlan(plan, 'workout_plan')
      setPlanId(id)
      setSaved(true)
    } catch (e) {
      setError('Failed to save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 border border-border rounded-2xl overflow-hidden bg-surface shadow-sm">
      <div className="flex items-center justify-between px-4 py-3 bg-brand">
        <span className="font-display font-bold text-white text-sm">Workout Plan</span>
        {!saved ? (
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-full bg-white text-brand font-semibold hover:bg-brand-light disabled:opacity-50 transition-colors shadow-sm"
          >
            {saving ? 'Saving…' : 'Save Plan'}
          </button>
        ) : (
          <span className="text-xs text-white font-semibold bg-white/20 rounded-full px-2.5 py-1">Saved</span>
        )}
      </div>

      {error && <p className="text-xs text-danger px-4 py-2">{error}</p>}

      <div className="divide-y divide-border">
        {plan.workout_days.map((day, i) => (
          <div key={i} className="px-4 py-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-display font-bold text-ink text-sm">{day.day}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-light text-brand-dark font-medium">{day.focus}</span>
            </div>
            <ul className="text-sm text-ink space-y-1">
              {day.exercises.map((ex, j) => (
                <li key={j} className="flex justify-between items-center gap-4">
                  <span>{ex.exercise_name}</span>
                  <span className="flex items-center gap-3 shrink-0">
                    <span className="text-ink-soft">{ex.sets} × {ex.reps} · rest {ex.rest_seconds}s</span>
                    {saved && (
                      <FeedbackButtons
                        planId={planId}
                        itemType="exercise"
                        itemName={ex.exercise_name}
                      />
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {plan.rest_days?.length > 0 && (
        <div className="px-4 py-2 bg-bg border-t border-border text-xs text-ink-soft">
          Rest days: {plan.rest_days.join(', ')}
        </div>
      )}

      {plan.notes && (
        <div className="px-4 py-3 bg-bg border-t border-border">
          <p className="text-xs text-ink-soft italic">{plan.notes}</p>
        </div>
      )}
    </div>
  )
}
