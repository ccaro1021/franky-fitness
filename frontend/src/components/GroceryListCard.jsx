const CATEGORY_ORDER = ['produce', 'protein', 'dairy', 'frozen', 'pantry']

const CATEGORY_LABELS = {
  produce: 'Produce',
  protein: 'Protein',
  dairy: 'Dairy',
  frozen: 'Frozen',
  pantry: 'Pantry',
}

const CATEGORY_ICONS = {
  produce: '🥦',
  protein: '🍗',
  dairy: '🧀',
  frozen: '🧊',
  pantry: '🥫',
}

function formatQuantity(qty) {
  return Number.isInteger(qty) ? qty : qty.toFixed(2)
}

function formatItem(item) {
  const qty = formatQuantity(item.total_quantity)
  if (item.unit === 'unit') {
    return `${qty} ${item.name}`
  }
  return `${qty} ${item.unit} ${item.name}`
}

export default function GroceryListCard({ groceryList }) {
  const byCategory = CATEGORY_ORDER.reduce((acc, cat) => {
    const items = groceryList.items.filter(item => item.category === cat)
    if (items.length) acc[cat] = items
    return acc
  }, {})

  return (
    <div className="mt-3 border border-border rounded-2xl overflow-hidden bg-surface shadow-sm">
      <div className="px-4 py-3 bg-success">
        <h3 className="font-display font-bold text-white text-sm">Grocery List</h3>
      </div>
      <div className="px-4 py-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Object.entries(byCategory).map(([cat, items]) => (
          <div key={cat}>
            <h4 className="text-xs font-semibold text-ink-soft uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
              <span>{CATEGORY_ICONS[cat]}</span>
              {CATEGORY_LABELS[cat]}
            </h4>
            <ul className="text-sm text-ink space-y-1">
              {items.map((item, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-success-light border border-success shrink-0" />
                  {formatItem(item)}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {groceryList.missing_meals?.length > 0 && (
        <div className="px-4 py-2 bg-warning-light border-t border-border text-xs text-warning font-medium">
          Couldn't fetch ingredients for: {groceryList.missing_meals.join(', ')}. Try again later.
        </div>
      )}
    </div>
  )
}
