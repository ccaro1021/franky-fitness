import { useEffect, useState } from 'react'
import { forgetPreference, getPreferences, getProfile, updateProfile } from '../api'

const PREFERENCE_GROUPS = [
  { key: 'liked_meals', label: 'Meals you liked', itemType: 'meal', tone: 'success' },
  { key: 'disliked_meals', label: 'Meals you disliked', itemType: 'meal', tone: 'danger' },
  { key: 'liked_workouts', label: 'Exercises you liked', itemType: 'exercise', tone: 'success' },
  { key: 'disliked_workouts', label: 'Exercises you disliked', itemType: 'exercise', tone: 'danger' },
]

const TONE_CLASSES = {
  success: 'bg-success-light text-success',
  danger: 'bg-danger-light text-danger',
}

function arrayToText(arr) {
  return (arr || []).join(', ')
}

function textToArray(text) {
  return text
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
}

function formatHeight(totalInches) {
  if (totalInches === null || totalInches === undefined || totalInches === '') return null
  const feet = Math.floor(totalInches / 12)
  const inches = totalInches - feet * 12
  const inchesStr = Number.isInteger(inches) ? inches : inches.toFixed(1)
  return `${feet}'${inchesStr}"`
}

const inputClass =
  'mt-1 w-full border border-border bg-bg rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:bg-surface transition-colors'

export default function ProfilePage({ showOnboardingBanner = false }) {
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [bmi, setBmi] = useState(null)

  const [heightFeet, setHeightFeet] = useState('')
  const [heightInchesPart, setHeightInchesPart] = useState('')
  const [weightLbs, setWeightLbs] = useState('')
  const [targetWeightLbs, setTargetWeightLbs] = useState('')
  const [fitnessGoals, setFitnessGoals] = useState('')
  const [dietaryRestrictions, setDietaryRestrictions] = useState('')
  const [notes, setNotes] = useState('')

  const [preferences, setPreferences] = useState(null)
  const [preferencesError, setPreferencesError] = useState(null)

  useEffect(() => {
    getProfile()
      .then(profile => {
        if (profile.height_inches == null) {
          setHeightFeet('')
          setHeightInchesPart('')
        } else {
          const feet = Math.floor(profile.height_inches / 12)
          const inches = profile.height_inches - feet * 12
          setHeightFeet(feet)
          setHeightInchesPart(Number.isInteger(inches) ? inches : Number(inches.toFixed(1)))
        }
        setWeightLbs(profile.weight_lbs ?? '')
        setTargetWeightLbs(profile.target_weight_lbs ?? '')
        setFitnessGoals(arrayToText(profile.fitness_goals))
        setDietaryRestrictions(arrayToText(profile.dietary_restrictions))
        setNotes(profile.notes || '')
        setBmi(profile.bmi)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))

    getPreferences()
      .then(setPreferences)
      .catch(e => setPreferencesError(e.message))
  }, [])

  async function handleForget(itemType, itemName) {
    try {
      const updated = await forgetPreference(itemType, itemName)
      setPreferences(updated)
    } catch (err) {
      setPreferencesError(err.message)
    }
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const totalHeightInches =
        heightFeet === '' && heightInchesPart === ''
          ? null
          : Number(heightFeet || 0) * 12 + Number(heightInchesPart || 0)
      const updated = await updateProfile({
        height_inches: totalHeightInches,
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
    return <div className="flex-1 flex items-center justify-center text-sm text-ink-soft">Loading…</div>
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-md mx-auto space-y-6">
        {showOnboardingBanner && !bannerDismissed && (
          <div className="bg-brand-light border border-brand/20 rounded-2xl px-4 py-3 flex items-start gap-3">
            <p className="text-sm text-ink flex-1">
              Welcome to Franky! Filling in your stats, goals, and dietary restrictions
              below helps Franky build meal and workout plans tailored to you — or you
              can skip this and share that info in chat instead.
            </p>
            <button
              type="button"
              onClick={() => setBannerDismissed(true)}
              title="Dismiss"
              className="text-ink-soft hover:text-ink leading-none shrink-0"
            >
              ×
            </button>
          </div>
        )}

        {/* Stats summary card */}
        <div className="bg-surface rounded-2xl border border-border shadow-sm p-5">
          <h2 className="font-display font-bold text-lg text-ink mb-4">Your Stats</h2>
          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="bg-brand-light rounded-xl py-3">
              <p className="text-xs font-semibold text-ink-soft uppercase tracking-wide">Height</p>
              <p className="font-display font-bold text-xl text-brand-dark mt-0.5">
                {formatHeight(heightFeet === '' && heightInchesPart === '' ? null : Number(heightFeet || 0) * 12 + Number(heightInchesPart || 0)) ?? '—'}
              </p>
            </div>
            <div className="bg-brand-light rounded-xl py-3">
              <p className="text-xs font-semibold text-ink-soft uppercase tracking-wide">Weight</p>
              <p className="font-display font-bold text-xl text-brand-dark mt-0.5">
                {weightLbs !== '' ? `${weightLbs}` : '—'}
                <span className="text-xs font-sans font-medium text-ink-soft ml-0.5">lbs</span>
              </p>
            </div>
            <div className="bg-brand-light rounded-xl py-3">
              <p className="text-xs font-semibold text-ink-soft uppercase tracking-wide">Target</p>
              <p className="font-display font-bold text-xl text-brand-dark mt-0.5">
                {targetWeightLbs !== '' ? `${targetWeightLbs}` : '—'}
                <span className="text-xs font-sans font-medium text-ink-soft ml-0.5">lbs</span>
              </p>
            </div>
            <div className="bg-brand-light rounded-xl py-3">
              <p className="text-xs font-semibold text-ink-soft uppercase tracking-wide">BMI</p>
              <p className="font-display font-bold text-xl text-brand-dark mt-0.5">{bmi ?? '—'}</p>
            </div>
          </div>
        </div>

        {/* Edit form */}
        <form onSubmit={handleSave} className="bg-surface rounded-2xl border border-border shadow-sm p-5 space-y-4">
          <h2 className="font-display font-bold text-lg text-ink">Edit Profile</h2>

          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-xs font-semibold text-ink-soft">Height</span>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="number"
                  step="1"
                  min="0"
                  placeholder="5"
                  value={heightFeet}
                  onChange={e => setHeightFeet(e.target.value)}
                  className={`${inputClass} mt-0 w-1/2`}
                />
                <span className="text-sm text-ink-soft">ft</span>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder="8"
                  value={heightInchesPart}
                  onChange={e => setHeightInchesPart(e.target.value)}
                  className={`${inputClass} mt-0 w-1/2`}
                />
                <span className="text-sm text-ink-soft">in</span>
              </div>
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-ink-soft">Weight (lbs)</span>
              <input
                type="number"
                step="0.1"
                value={weightLbs}
                onChange={e => setWeightLbs(e.target.value)}
                className={inputClass}
              />
            </label>
          </div>

          <label className="block">
            <span className="text-xs font-semibold text-ink-soft">Target weight (lbs)</span>
            <input
              type="number"
              step="0.1"
              value={targetWeightLbs}
              onChange={e => setTargetWeightLbs(e.target.value)}
              className={inputClass}
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold text-ink-soft">Fitness goals (comma-separated)</span>
            <input
              type="text"
              value={fitnessGoals}
              onChange={e => setFitnessGoals(e.target.value)}
              placeholder="lose fat, build muscle"
              className={inputClass}
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold text-ink-soft">Dietary restrictions (comma-separated)</span>
            <input
              type="text"
              value={dietaryRestrictions}
              onChange={e => setDietaryRestrictions(e.target.value)}
              placeholder="vegetarian, no shellfish"
              className={inputClass}
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold text-ink-soft">Notes</span>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              className={`${inputClass} resize-none`}
            />
          </label>

          {error && <p className="text-sm text-danger bg-danger-light rounded-lg px-3 py-2">{error}</p>}
          {saved && <p className="text-sm text-success bg-success-light rounded-lg px-3 py-2">Saved!</p>}

          <button
            type="submit"
            disabled={saving}
            className="bg-brand text-white rounded-xl px-4 py-2.5 text-sm font-semibold hover:bg-brand-dark disabled:opacity-50 transition-colors shadow-sm"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </form>

        {/* Preferences */}
        <div className="bg-surface rounded-2xl border border-border shadow-sm p-5 space-y-4">
          <div>
            <h2 className="font-display font-bold text-lg text-ink">What Franky Knows About You</h2>
            <p className="text-sm text-ink-soft mt-1">
              Based on your 👍/👎 feedback. Remove anything that doesn't seem right —
              Franky will stop factoring it into future plans.
            </p>
          </div>

          {preferencesError && <p className="text-sm text-danger">{preferencesError}</p>}

          {preferences && PREFERENCE_GROUPS.every(g => preferences[g.key].length === 0) && (
            <p className="text-sm text-ink-soft">
              No feedback yet — rate meals and exercises in your saved plans to teach Franky your preferences.
            </p>
          )}

          {preferences && PREFERENCE_GROUPS.map(group => (
            preferences[group.key].length > 0 && (
              <div key={group.key}>
                <h3 className="text-xs font-semibold text-ink-soft mb-1.5">{group.label}</h3>
                <div className="flex flex-wrap gap-2">
                  {preferences[group.key].map(itemName => (
                    <span
                      key={itemName}
                      className={`inline-flex items-center gap-1.5 rounded-full pl-3 pr-2 py-1 text-sm font-medium ${TONE_CLASSES[group.tone]}`}
                    >
                      {itemName}
                      <button
                        type="button"
                        onClick={() => handleForget(group.itemType, itemName)}
                        title="Remove this preference"
                        className="opacity-50 hover:opacity-100 leading-none"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )
          ))}
        </div>
      </div>
    </div>
  )
}
