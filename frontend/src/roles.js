// One place that decides what each role sees. Sidebar, routing and the
// landing page all read from here, so the three interfaces cannot drift.
// The backend still enforces every permission; this only shapes the UI.

export const ROLE_META = {
  employee: { label: 'Employee', tagline: 'Your expenses' },
  manager: { label: 'Manager', tagline: 'Team spending & approvals' },
  admin: { label: 'Admin', tagline: 'Payments & people' },
}

export const NAV = {
  employee: [
    { id: 'overview', path: '/overview', label: 'Overview', section: 'My workspace' },
    { id: 'my-expenses', path: '/expenses', label: 'My expenses', section: 'My workspace' },
  ],
  manager: [
    { id: 'dashboard', path: '/dashboard', label: 'Spending dashboard', section: 'Insights' },
    { id: 'queue', path: '/queue', label: 'Approval queue', section: 'Review', badge: 'pending' },
    { id: 'all', path: '/expenses', label: 'All expenses', section: 'Review' },
  ],
  admin: [
    { id: 'dashboard', path: '/dashboard', label: 'Spending dashboard', section: 'Insights' },
    { id: 'queue', path: '/queue', label: 'Approval queue', section: 'Review', badge: 'pending' },
    { id: 'payments', path: '/payments', label: 'Payments', section: 'Finance', badge: 'payable' },
    { id: 'all', path: '/expenses', label: 'All expenses', section: 'Review' },
    { id: 'people', path: '/people', label: 'People & roles', section: 'Administration' },
  ],
}

export const HOME = {
  employee: '/overview',
  manager: '/dashboard',
  admin: '/dashboard',
}

export const isReviewer = (user) => user.role === 'manager' || user.role === 'admin'
