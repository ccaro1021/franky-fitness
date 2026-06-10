import { useState } from 'react'
import { savePlan, getGroceryList } from '../api'
import GroceryListCard from './GroceryListCard'
import FeedbackButtons from './FeedbackButtons'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'snack']

export default function MealPlanCard({ plan }) {
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [planId, setPlanId] = useState(null)
  const [groceryList, setGroceryList] = useState(null)
  const [loadingGroceryList, setLoadingGroceryList] = useState(false)

  const byDay = DAYS.reduce((acc, day) => {
    const meals = plan.meals.filter(m => m.day === day).sort(
      (a, b) => MEAL_ORDER.indexOf(a.meal_type) - MEAL_ORDER.indexOf(b.meal_type)
    )
    if (meals.length) acc[day] = meals
    return acc
  }, {})

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const { id } = await savePlan(plan)
      setPlanId(id)
      setSaved(true)
    } catch (e) {
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
    } catch (e) {
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
            disabled={saving}
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
              <th className="px-4 py-2 font-medium text-right">Feedback</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {Object.entries(byDay).map(([day, meals]) =>
              meals.map((meal, i) => (
                <tr key={`${day}-${meal.meal_type}`} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 text-gray-600 font-medium">
                    {i === 0 ? day : ''}
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
                    {saved && (
                      <FeedbackButtons
                        planId={planId}
                        itemType="meal"
                        itemName={meal.name}
                      />
                    )}
                  </td>
                </tr>
              ))
            )}
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
