import { Fragment, useEffect, useState } from 'react'
import { savePlan, getGroceryList, getMealAlternatives } from '../api'
import GroceryListCard from './GroceryListCard'
import FeedbackButtons from './FeedbackButtons'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'snack']

function SwapPanel({ meal, onSelect, onClose }) {
  const [query, setQuery] = useState('')
  const [candidates, setCandidates] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const mealType = meal.meal_type
  const mealCalories = meal.calories

  function search(q) {
    setLoading(true)
    setError(null)
    getMealAlternatives({ mealType, maxCalories: mealCalories, query: q })
      .then(setCandidates)
      .catch(() => setError("Couldn't load alternatives."))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getMealAlternatives({ mealType, maxCalories: mealCalories, query: '' })
      .then(setCandidates)
      .catch(() => setError("Couldn't load alternatives."))
      .finally(() => setLoading(false))
  }, [mealType, mealCalories])

  return (
    <tr className="bg-brand-light">
      <td colSpan={8} className="px-4 py-3">
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search(query)}
            placeholder={`Refine search (default: "${meal.meal_type}")`}
            className="flex-1 text-xs border border-border bg-surface rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand"
          />
          <button
            onClick={() => search(query)}
            disabled={loading}
            className="text-xs px-2 py-1 rounded-lg bg-surface text-ink-soft border border-border hover:bg-bg disabled:opacity-50"
          >
            Search
          </button>
          <button
            onClick={onClose}
            className="text-xs px-2 py-1 rounded-lg text-ink-soft hover:text-ink"
          >
            Cancel
          </button>
        </div>

        {loading && <p className="text-xs text-ink-soft">Searching…</p>}

        {error && (
          <p className="text-xs text-danger">
            {error}{' '}
            <button onClick={() => search(query)} className="underline">
              Retry
            </button>
          </p>
        )}

        {!loading && !error && candidates && (
          candidates.length === 0 ? (
            <p className="text-xs text-ink-soft">No alternatives found.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {candidates.map((c, i) => (
                <div
                  key={c.spoonacular_id ?? i}
                  className="border border-border rounded-xl px-3 py-2 bg-surface flex items-center justify-between gap-2"
                >
                  <div>
                    <p className="text-sm text-ink">{c.name}</p>
                    <p className="text-xs text-ink-soft">
                      {c.calories_per_serving} cal · {c.protein_g}g P · {c.carbs_g}g C · {c.fat_g}g F
                    </p>
                  </div>
                  <button
                    onClick={() => onSelect(c)}
                    className="text-xs px-2 py-1 rounded-lg bg-brand text-white hover:bg-brand-dark shrink-0 font-semibold"
                  >
                    Use this
                  </button>
                </div>
              ))}
            </div>
          )
        )}
      </td>
    </tr>
  )
}

export default function MealPlanCard({ plan, savedPlanId = null, initiallySaved = false }) {
  const [meals, setMeals] = useState(plan.meals)
  const [saved, setSaved] = useState(initiallySaved)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [planId, setPlanId] = useState(savedPlanId)
  const [groceryList, setGroceryList] = useState(null)
  const [loadingGroceryList, setLoadingGroceryList] = useState(false)
  const [swapOpenKey, setSwapOpenKey] = useState(null)

  const byDay = DAYS.reduce((acc, day) => {
    const dayMeals = meals.filter(m => m.day === day).sort(
      (a, b) => MEAL_ORDER.indexOf(a.meal_type) - MEAL_ORDER.indexOf(b.meal_type)
    )
    if (dayMeals.length) acc[day] = dayMeals
    return acc
  }, {})

  function handleRemoveMeal(day, mealType) {
    setMeals(meals.filter(m => !(m.day === day && m.meal_type === mealType)))
    setSwapOpenKey(null)
  }

  function handleRemoveDay(day) {
    setMeals(meals.filter(m => m.day !== day))
    setSwapOpenKey(null)
  }

  function handleSwapSelect(day, mealType, candidate) {
    setMeals(meals.map(m => (
      m.day === day && m.meal_type === mealType
        ? {
            ...m,
            name: candidate.name,
            calories: candidate.calories_per_serving,
            protein_g: candidate.protein_g,
            carbs_g: candidate.carbs_g,
            fat_g: candidate.fat_g,
            spoonacular_id: candidate.spoonacular_id,
            ingredients_fetched: false,
          }
        : m
    )))
    setSwapOpenKey(null)
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const { id } = await savePlan({ ...plan, meals })
      setPlanId(id)
      setSaved(true)
    } catch {
      setError('Failed to save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  async function handleGroceryList() {
    setLoadingGroceryList(true)
    setError(null)
    try {
      const data = await getGroceryList(planId)
      setGroceryList(data)
    } catch {
      setError('Failed to load grocery list. Try again.')
    } finally {
      setLoadingGroceryList(false)
    }
  }

  return (
    <div className="mt-3 border border-border rounded-2xl overflow-hidden bg-surface shadow-sm">
      <div className="flex items-center justify-between px-4 py-3 bg-brand">
        <span className="font-display font-bold text-white text-sm">Weekly Meal Plan</span>
        {!saved ? (
          <button
            onClick={handleSave}
            disabled={saving || meals.length === 0}
            className="text-xs px-3 py-1.5 rounded-full bg-white text-brand font-semibold hover:bg-brand-light disabled:opacity-50 transition-colors shadow-sm"
          >
            {saving ? 'Saving…' : 'Save Plan'}
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-xs text-white font-semibold bg-white/20 rounded-full px-2.5 py-1">Saved</span>
            {!groceryList && (
              <button
                onClick={handleGroceryList}
                disabled={loadingGroceryList}
                className="text-xs px-3 py-1.5 rounded-full bg-white text-brand font-semibold hover:bg-brand-light disabled:opacity-50 transition-colors shadow-sm"
              >
                {loadingGroceryList ? 'Loading…' : 'Grocery List'}
              </button>
            )}
          </div>
        )}
      </div>

      {error && <p className="text-xs text-danger px-4 py-2">{error}</p>}

      {!saved && meals.length === 0 && (
        <p className="text-xs text-ink-soft px-4 py-2">Add at least one meal to save this plan.</p>
      )}

      {!saved && (
        <p className="text-xs text-ink-soft px-4 pt-2">
          Swap or remove any meal or day below before saving.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-bg text-left text-xs text-ink-soft uppercase tracking-wide">
              <th className="px-4 py-2 font-semibold">Day</th>
              <th className="px-4 py-2 font-semibold">Meal</th>
              <th className="px-4 py-2 font-semibold">Name</th>
              <th className="px-4 py-2 font-semibold text-right">Cal</th>
              <th className="px-4 py-2 font-semibold text-right">Protein</th>
              <th className="px-4 py-2 font-semibold text-right">Carbs</th>
              <th className="px-4 py-2 font-semibold text-right">Fat</th>
              <th className="px-4 py-2 font-semibold text-right">{saved ? 'Feedback' : 'Actions'}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {Object.entries(byDay).map(([day, dayMeals]) => {
              const totals = dayMeals.reduce(
                (acc, m) => ({
                  calories: acc.calories + m.calories,
                  protein_g: acc.protein_g + m.protein_g,
                  carbs_g: acc.carbs_g + m.carbs_g,
                  fat_g: acc.fat_g + m.fat_g,
                }),
                { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }
              )

              return (
                <Fragment key={day}>
                  {dayMeals.map((meal, i) => {
                    const key = `${day}-${meal.meal_type}`
                    return (
                      <Fragment key={key}>
                        <tr className="hover:bg-bg transition-colors">
                          <td className="px-4 py-2.5 text-ink font-semibold">
                            {i === 0 ? (
                              <span className="inline-flex items-center gap-1.5">
                                {day}
                                {!saved && (
                                  <button
                                    onClick={() => handleRemoveDay(day)}
                                    title="Remove this day"
                                    className="text-ink-soft/40 hover:text-danger leading-none"
                                  >
                                    ×
                                  </button>
                                )}
                              </span>
                            ) : ''}
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="capitalize text-xs px-2 py-0.5 rounded-full bg-brand-light text-brand-dark font-medium">
                              {meal.meal_type}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-ink">{meal.name}</td>
                          <td className="px-4 py-2.5 text-right text-ink-soft">{meal.calories}</td>
                          <td className="px-4 py-2.5 text-right">
                            <span className="text-protein font-semibold">{meal.protein_g}g</span>
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            <span className="text-carbs font-semibold">{meal.carbs_g}g</span>
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            <span className="text-fat font-semibold">{meal.fat_g}g</span>
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            {saved ? (
                              <FeedbackButtons
                                planId={planId}
                                itemType="meal"
                                itemName={meal.name}
                              />
                            ) : (
                              <span className="inline-flex items-center gap-2 text-xs">
                                <button
                                  onClick={() => setSwapOpenKey(swapOpenKey === key ? null : key)}
                                  className="text-brand hover:text-brand-dark font-semibold"
                                >
                                  Swap
                                </button>
                                <button
                                  onClick={() => handleRemoveMeal(day, meal.meal_type)}
                                  title="Remove this meal"
                                  className="text-ink-soft/40 hover:text-danger leading-none"
                                >
                                  ×
                                </button>
                              </span>
                            )}
                          </td>
                        </tr>
                        {swapOpenKey === key && (
                          <SwapPanel
                            meal={meal}
                            onSelect={c => handleSwapSelect(day, meal.meal_type, c)}
                            onClose={() => setSwapOpenKey(null)}
                          />
                        )}
                      </Fragment>
                    )
                  })}
                  <tr className="bg-bg text-xs font-semibold text-ink-soft">
                    <td className="px-4 py-1.5" colSpan={3}>Total</td>
                    <td className="px-4 py-1.5 text-right">{totals.calories}</td>
                    <td className="px-4 py-1.5 text-right text-protein">{totals.protein_g}g</td>
                    <td className="px-4 py-1.5 text-right text-carbs">{totals.carbs_g}g</td>
                    <td className="px-4 py-1.5 text-right text-fat">{totals.fat_g}g</td>
                    <td className="px-4 py-1.5"></td>
                  </tr>
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {plan.notes && (
        <div className="px-4 py-3 bg-bg border-t border-border">
          <p className="text-xs text-ink-soft italic">{plan.notes}</p>
        </div>
      )}

      {groceryList && <GroceryListCard groceryList={groceryList} />}
    </div>
  )
}
