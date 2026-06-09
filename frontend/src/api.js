export async function sendMessage(messages, person) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, person }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Chat request failed')
  }
  return res.json()
}

export async function savePlan(person, plan) {
  const res = await fetch('/api/plans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ person, plan }),
  })
  if (!res.ok) throw new Error('Failed to save plan')
  return res.json()
}

export async function listPlans(person) {
  const res = await fetch(`/api/plans?person=${encodeURIComponent(person)}`)
  if (!res.ok) throw new Error('Failed to load plans')
  return res.json()
}
