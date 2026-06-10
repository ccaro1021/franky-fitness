const CATEGORY_ORDER = ['produce', 'protein', 'dairy', 'frozen', 'pantry']

const CATEGORY_LABELS = {
  produce: 'Produce',
  protein: 'Protein',
  dairy: 'Dairy',
  frozen: 'Frozen',
  pantry: 'Pantry',
}

function formatQuantity(qty) {
  return Number.isInteger(qty) ? qty : qty.toFixed(2)
}

export default function GroceryListCard({ groceryList }) {
  const byCategory = CATEGORY_ORDER.reduce((acc, cat) => {
    const items = groceryList.items.filter(item => item.category === cat)
    if (items.length) acc[cat] = items
    return acc
  }, {})

  return (
    <div className="mt-3 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <div className="px-4 py-3 bg-amber-50 border-b border-gray-200">
        <h3 className="font-semibold text-amber-900 text-sm">Grocery List</h3>
      </div>
      <div className="px-4 py-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Object.entries(byCategory).map(([cat, items]) => (
          <div key={cat}>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              {CATEGORY_LABELS[cat]}
            </h4>
            <ul className="text-sm text-gray-700 space-y-1">
              {items.map((item, i) => (
                <li key={i}>
                  {formatQuantity(item.total_quantity)} {item.unit} {item.name}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
