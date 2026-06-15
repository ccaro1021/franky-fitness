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
    <tr className="bg-gray-50">
      <td colSpan={8} className="px-4 py-3">
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search(query)}
            placeholder={`Refine search (default: "${meal.meal_type}")`}
            className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            onClick={() => search(query)}
            disabled={loading}
            className="text-xs px-2 py-1 rounded bg-gray-200 text-gray-700 hover:bg-gray-300 disabled:opacity-50"
          >
            Search
          </button>
          <button
            onClick={onClose}
            className="text-xs px-2 py-1 rounded text-gray-400 hover:text-gray-600"
          >
            Cancel
          </button>
        </div>

        {loading && <p className="text-xs text-gray-400">Searching…</p>}

        {error && (
          <p className="text-xs text-red-600">
            {error}{' '}
            <button onClick={() => search(query)} className="underline">
              Retry
            </button>
          </p>
        )}

        {!loading && !error && candidates && (
          candidates.length === 0 ? (
            <p className="text-xs text-gray-400">No alternatives found.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {candidates.map((c, i) => (
                <div
                  key={c.spoonacular_id ?? i}
                  className="border border-gray-200 rounded-lg px-3 py-2 bg-white flex items-center justify-between gap-2"
                >
                  <div>
                    <p className="text-sm text-gray-800">{c.name}</p>
                    <p className="text-xs text-gray-500">
                      {c.calories_per_serving} cal · {c.protein_g}g P · {c.carbs_g}g C · {c.fat_g}g F
                    </p>
                  </div>
                  <button
                    onClick={() => onSelect(c)}
                    className="text-xs px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 shrink-0"
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

export default function MealPlanCard({ plan }) {
  const [meals, setMeals] = useState(plan.meals)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [planId, setPlanId] = useState(null)
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
    <div className="mt-3 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <div className="flex items-center justify-between px-4 py-3 bg-emerald-50 border-b border-gray-200">
        <span className="font-semibold text-emerald-800 text-sm">Weekly Meal Plan</span>
        {!saved ? (
          <button
            onClick={handleSave}
            disabled={saving || meals.length === 0}
            className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving…' : 'Save Plan'}
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-xs text-emerald-700 font-medium">Saved</span>
            {!groceryList && (
              <button
                onClick={handleGroceryList}
                disabled={loadingGroceryList}
                className="text-xs px-3 py-1.5 rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 transition-colors"
              >
                {loadingGroceryList ? 'Loading…' : 'Grocery List'}
              </button>
            )}
          </div>
        )}
      </div>

      {error && <p className="text-xs text-red-600 px-4 py-2">{error}</p>}

      {!saved && meals.length === 0 && (
        <p className="text-xs text-gray-400 px-4 py-2">Add at least one meal to save this plan.</p>
      )}

      {!saved && (
        <p className="text-xs text-gray-400 px-4 pt-2">
          Swap or remove any meal or day below before saving.
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-2 font-medium">Day</th>
              <th className="px-4 py-2 font-medium">Meal</th>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium text-right">Cal</th>
              <th className="px-4 py-2 font-medium text-right">Protein</th>
              <th className="px-4 py-2 font-medium text-right">Carbs</th>
              <th className="px-4 py-2 font-medium text-right">Fat</th>
              <th className="px-4 py-2 font-medium text-right">{saved ? 'Feedback' : 'Actions'}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
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
                        <tr className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-2.5 text-gray-600 font-medium">
                            {i === 0 ? (
                              <span className="inline-flex items-center gap-1.5">
                                {day}
                                {!saved && (
                                  <button
                                    onClick={() => handleRemoveDay(day)}
                                    title="Remove this day"
                                    className="text-gray-300 hover:text-red-500 leading-none"
                                  >
                                    ×
                                  </button>
                                )}
                              </span>
                            ) : ''}
                          </td>
                          <td className="px-4 py-2.5">
                            <span className="capitalize text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                              {meal.meal_type}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-gray-800">{meal.name}</td>
                          <td className="px-4 py-2.5 text-right text-gray-600">{meal.calories}</td>
                          <td className="px-4 py-2.5 text-right text-blue-600 font-medium">{meal.protein_g}g</td>
                          <td className="px-4 py-2.5 text-right text-amber-600">{meal.carbs_g}g</td>
                          <td className="px-4 py-2.5 text-right text-gray-500">{meal.fat_g}g</td>
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
                                  className="text-emerald-600 hover:text-emerald-700"
                                >
                                  Swap
                                </button>
                                <button
                                  onClick={() => handleRemoveMeal(day, meal.meal_type)}
                                  title="Remove this meal"
                                  className="text-gray-300 hover:text-red-500 leading-none"
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
                  <tr className="bg-gray-50 text-xs font-medium text-gray-500">
                    <td className="px-4 py-1.5" colSpan={3}>Total</td>
                    <td className="px-4 py-1.5 text-right">{totals.calories}</td>
                    <td className="px-4 py-1.5 text-right text-blue-600">{totals.protein_g}g</td>
                    <td className="px-4 py-1.5 text-right text-amber-600">{totals.carbs_g}g</td>
                    <td className="px-4 py-1.5 text-right">{totals.fat_g}g</td>
                    <td className="px-4 py-1.5"></td>
                  </tr>
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {plan.notes && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-500 italic">{plan.notes}</p>
        </div>
      )}

      {groceryList && <GroceryListCard groceryList={groceryList} />}
    </div>
  )
}
