import { useEffect, useState } from 'react'
import { getProfile, updateProfile } from '../api'

function arrayToText(arr) {
  return (arr || []).join(', ')
}

function textToArray(text) {
  return text
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
}

export default function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [bmi, setBmi] = useState(null)

  const [heightInches, setHeightInches] = useState('')
  const [weightLbs, setWeightLbs] = useState('')
  const [targetWeightLbs, setTargetWeightLbs] = useState('')
  const [fitnessGoals, setFitnessGoals] = useState('')
  const [dietaryRestrictions, setDietaryRestrictions] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    getProfile()
      .then(profile => {
        setHeightInches(profile.height_inches ?? '')
        setWeightLbs(profile.weight_lbs ?? '')
        setTargetWeightLbs(profile.target_weight_lbs ?? '')
        setFitnessGoals(arrayToText(profile.fitness_goals))
        setDietaryRestrictions(arrayToText(profile.dietary_restrictions))
        setNotes(profile.notes || '')
        setBmi(profile.bmi)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const updated = await updateProfile({
        height_inches: heightInches === '' ? null : Number(heightInches),
        weight_lbs: weightLbs === '' ? null : Number(weightLbs),
        target_weight_lbs: targetWeightLbs === '' ? null : Number(targetWeightLbs),
        fitness_goals: textToArray(fitnessGoals),
        dietary_restrictions: textToArray(dietaryRestrictions),
        notes,
      })
      setBmi(updated.bmi)
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-sm text-gray-400">Loading…</div>
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <form onSubmit={handleSave} className="max-w-md mx-auto space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Your Profile</h2>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs font-medium text-gray-500">Height (in)</span>
            <input
              type="number"
              step="0.1"
              value={heightInches}
              onChange={e => setHeightInches(e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-500">Weight (lbs)</span>
            <input
              type="number"
              step="0.1"
              value={weightLbs}
              onChange={e => setWeightLbs(e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs font-medium text-gray-500">Target weight (lbs)</span>
            <input
              type="number"
              step="0.1"
              value={targetWeightLbs}
              onChange={e => setTargetWeightLbs(e.target.value)}
              className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </label>
          <div>
            <span className="text-xs font-medium text-gray-500">BMI</span>
            <div className="mt-1 w-full border border-gray-100 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-600">
              {bmi ?? '—'}
            </div>
          </div>
        </div>

        <label className="block">
          <span className="text-xs font-medium text-gray-500">Fitness goals (comma-separated)</span>
          <input
            type="text"
            value={fitnessGoals}
            onChange={e => setFitnessGoals(e.target.value)}
            placeholder="lose fat, build muscle"
            className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-gray-500">Dietary restrictions (comma-separated)</span>
          <input
            type="text"
            value={dietaryRestrictions}
            onChange={e => setDietaryRestrictions(e.target.value)}
            placeholder="vegetarian, no shellfish"
            className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-gray-500">Notes</span>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={3}
            className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {saved && <p className="text-sm text-emerald-600">Saved!</p>}

        <button
          type="submit"
          disabled={saving}
          className="bg-emerald-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
      </form>
    </div>
  )
}
