import { useState } from 'react'
import { saveRecipe } from '../api'

export default function RecipeCard({ recipe, initiallySaved = false }) {
  const [saved, setSaved] = useState(initiallySaved)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const steps = recipe.recipe
    ? recipe.recipe.split('\n').filter(line => line.trim())
    : []

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      await saveRecipe(recipe)
      setSaved(true)
    } catch {
      setError('Failed to save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 border border-border rounded-2xl overflow-hidden bg-surface shadow-sm">
      <div className="px-4 py-3 bg-brand">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-display font-bold text-white text-sm">{recipe.name}</h3>
          {!saved ? (
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-xs px-3 py-1.5 rounded-full bg-white text-brand font-semibold hover:bg-brand-light disabled:opacity-50 transition-colors shadow-sm shrink-0"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          ) : (
            <span className="text-xs text-white font-semibold bg-white/20 rounded-full px-2.5 py-1 shrink-0">Saved</span>
          )}
        </div>
        {error && <p className="text-xs text-white/90 mt-1">{error}</p>}
        <div className="flex gap-3 mt-1.5 text-xs">
          <span className="text-white/80">{recipe.calories_per_serving} kcal</span>
          <span className="bg-white/20 text-white font-semibold rounded-full px-2 py-0.5">{recipe.protein_g}g protein</span>
          <span className="text-white/80">{recipe.carbs_g}g carbs</span>
          <span className="text-white/80">{recipe.fat_g}g fat</span>
        </div>
      </div>

      <div className="p-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Ingredients */}
        <div>
          <h4 className="text-xs font-semibold text-ink-soft uppercase tracking-wide mb-2">
            Ingredients
          </h4>
          <ul className="space-y-1">
            {recipe.ingredients.map((ing, i) => (
              <li key={i} className="text-sm text-ink flex gap-1.5">
                <span className="text-brand shrink-0">·</span>
                <span>
                  {ing.quantity_per_serving} {ing.unit} {ing.name}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Instructions */}
        <div>
          <h4 className="text-xs font-semibold text-ink-soft uppercase tracking-wide mb-2">
            Instructions
          </h4>
          <ol className="space-y-2">
            {steps.map((step, i) => (
              <li key={i} className="text-sm text-ink flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-brand-light text-brand-dark text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <span>{step.replace(/^\d+\.\s*/, '')}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  )
}
