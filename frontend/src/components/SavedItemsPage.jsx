import { useEffect, useState } from 'react'
import { deletePlan, deleteSavedRecipe, listPlans, listSavedRecipes } from '../api'
import MealPlanCard from './MealPlanCard'
import WorkoutPlanCard from './WorkoutPlanCard'
import RecipeCard from './RecipeCard'

const TABS = [
  { key: 'meal_plan', label: 'Meal Plans' },
  { key: 'workout_plan', label: 'Workout Plans' },
  { key: 'recipe', label: 'Recipes' },
]

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function summarize(tab, content) {
  if (tab === 'meal_plan') {
    const meals = content.meals || []
    const days = new Set(meals.map(m => m.day)).size
    return `${meals.length} meal${meals.length === 1 ? '' : 's'} across ${days} day${days === 1 ? '' : 's'}`
  }
  if (tab === 'workout_plan') {
    const days = (content.workout_days || []).length
    return `${days} workout day${days === 1 ? '' : 's'}`
  }
  return `${content.calories_per_serving} kcal · ${content.protein_g}g protein · ${content.carbs_g}g carbs · ${content.fat_g}g fat`
}

function title(tab, content) {
  return tab === 'recipe' ? content.name : null
}

export default function SavedItemsPage() {
  const [tab, setTab] = useState('meal_plan')
  const [itemsByTab, setItemsByTab] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => {
    if (itemsByTab[tab]) return

    setLoading(true)
    setError(null)
    const fetcher = tab === 'recipe' ? listSavedRecipes() : listPlans(tab)
    fetcher
      .then(items => setItemsByTab(prev => ({ ...prev, [tab]: items })))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [tab, itemsByTab])

  async function handleDelete(id) {
    if (!window.confirm('Delete this saved item? This cannot be undone.')) return

    try {
      if (tab === 'recipe') {
        await deleteSavedRecipe(id)
      } else {
        await deletePlan(id)
      }
      setItemsByTab(prev => ({ ...prev, [tab]: prev[tab].filter(item => item.id !== id) }))
      if (expandedId === id) setExpandedId(null)
    } catch (e) {
      setError(e.message)
    }
  }

  const items = itemsByTab[tab] || []

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex items-center gap-1 bg-surface border border-border rounded-full p-1 w-fit">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => { setTab(t.key); setExpandedId(null) }}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${
                tab === t.key ? 'bg-brand text-white shadow-sm' : 'text-ink-soft hover:text-ink'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading && <p className="text-sm text-ink-soft">Loading…</p>}

        {error && (
          <p className="text-sm text-danger bg-danger-light rounded-lg px-3 py-2">{error}</p>
        )}

        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-ink-soft">
            {tab === 'meal_plan' && "No saved meal plans yet — save one from the chat."}
            {tab === 'workout_plan' && "No saved workout plans yet — save one from the chat."}
            {tab === 'recipe' && "No saved recipes yet — ask Franky how to make a meal, then save it."}
          </p>
        )}

        <div className="space-y-2">
          {items.map(item => (
            <div key={item.id} className="bg-surface rounded-2xl border border-border shadow-sm overflow-hidden">
              <button
                onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-bg transition-colors"
              >
                <div className="min-w-0">
                  {title(tab, item.content) && (
                    <p className="font-display font-bold text-sm text-ink truncate">{title(tab, item.content)}</p>
                  )}
                  <p className="text-sm text-ink-soft truncate">
                    Saved {formatDate(item.created_at)} — {summarize(tab, item.content)}
                  </p>
                </div>
                <span className="flex items-center gap-3 shrink-0">
                  <span
                    role="button"
                    onClick={e => { e.stopPropagation(); handleDelete(item.id) }}
                    title="Remove"
                    className="text-ink-soft/40 hover:text-danger leading-none text-lg"
                  >
                    ×
                  </span>
                  <span className="text-ink-soft text-xs">{expandedId === item.id ? '▲' : '▼'}</span>
                </span>
              </button>

              {expandedId === item.id && (
                <div className="px-4 pb-4">
                  {tab === 'meal_plan' && (
                    <MealPlanCard plan={item.content} savedPlanId={item.id} initiallySaved />
                  )}
                  {tab === 'workout_plan' && (
                    <WorkoutPlanCard plan={item.content} savedPlanId={item.id} initiallySaved />
                  )}
                  {tab === 'recipe' && (
                    <RecipeCard recipe={item.content} initiallySaved />
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
