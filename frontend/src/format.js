export const STATUSES = ['all', 'submitted', 'approved', 'reimbursed', 'rejected']
export const CATEGORIES = ['travel', 'meals', 'accommodation', 'equipment', 'training', 'software', 'other']

export function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0)
}

export function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(
    new Date(value)
  )
}

export function initials(name = 'Passbook user') {
  return name
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function titleCase(value = '') {
  return value ? value[0].toUpperCase() + value.slice(1) : value
}
