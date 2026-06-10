export async function signup(email, password, name) {
  const res = await fetch('/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password, name }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Signup failed')
  }
  return res.json()
}

export async function login(email, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Login failed')
  }
  return res.json()
}

export async function logout() {
  const res = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) throw new Error('Logout failed')
  return res.json()
}

export async function getCurrentUser() {
  const res = await fetch('/api/auth/me', { credentials: 'include' })
  if (!res.ok) return null
  return res.json()
}

export async function getProfile() {
  const res = await fetch('/api/profile', { credentials: 'include' })
  if (!res.ok) throw new Error('Failed to load profile')
  return res.json()
}

export async function updateProfile(profile) {
  const res = await fetch('/api/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(profile),
  })
  if (!res.ok) throw new Error('Failed to update profile')
  return res.json()
}

export async function sendMessage(messages) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ messages }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Chat request failed')
  }
  return res.json()
}

export async function savePlan(plan, type = 'meal_plan') {
  const res = await fetch('/api/plans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ plan, type }),
  })
  if (!res.ok) throw new Error('Failed to save plan')
  return res.json()
}

export async function listPlans(type = 'meal_plan') {
  const res = await fetch(`/api/plans?type=${encodeURIComponent(type)}`, {
    credentials: 'include',
  })
  if (!res.ok) throw new Error('Failed to load plans')
  return res.json()
}

export async function getGroceryList(planId) {
  const res = await fetch(`/api/plans/${planId}/grocery-list`, {
    credentials: 'include',
  })
  if (!res.ok) throw new Error('Failed to load grocery list')
  return res.json()
}

export async function submitFeedback(planId, itemType, itemName, rating, note = null) {
  const res = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      plan_id: planId,
      item_type: itemType,
      item_name: itemName,
      rating,
      note,
    }),
  })
  if (!res.ok) throw new Error('Failed to submit feedback')
  return res.json()
}
