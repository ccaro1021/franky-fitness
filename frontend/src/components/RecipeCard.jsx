export default function RecipeCard({ recipe }) {
  const steps = recipe.recipe
    ? recipe.recipe.split('\n').filter(line => line.trim())
    : []

  return (
    <div className="mt-3 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <div className="px-4 py-3 bg-blue-50 border-b border-gray-200">
        <h3 className="font-semibold text-blue-900 text-sm">{recipe.name}</h3>
        <div className="flex gap-3 mt-1 text-xs text-blue-700">
          <span>{recipe.calories_per_serving} kcal</span>
          <span className="font-medium text-blue-800">{recipe.protein_g}g protein</span>
          <span>{recipe.carbs_g}g carbs</span>
          <span>{recipe.fat_g}g fat</span>
        </div>
      </div>

      <div className="p-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Ingredients */}
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Ingredients
          </h4>
          <ul className="space-y-1">
            {recipe.ingredients.map((ing, i) => (
              <li key={i} className="text-sm text-gray-700 flex gap-1.5">
                <span className="text-gray-400 shrink-0">·</span>
                <span>
                  {ing.quantity_per_serving} {ing.unit} {ing.name}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Instructions */}
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Instructions
          </h4>
          <ol className="space-y-2">
            {steps.map((step, i) => (
              <li key={i} className="text-sm text-gray-700 flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs flex items-center justify-center font-medium">
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
