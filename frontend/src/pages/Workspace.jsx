import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Sidebar from '../components/Sidebar.jsx'
import ApprovalQueue from '../components/ApprovalQueue.jsx'
import PeoplePanel from '../components/PeoplePanel.jsx'
import ExpenseBrowser from '../components/ExpenseBrowser.jsx'
import ExpenseFormModal from '../components/ExpenseFormModal.jsx'
import ExpenseDetailModal from '../components/ExpenseDetailModal.jsx'
import { Toast, PageHead } from '../components/ui.jsx'
import EmployeeOverview from './EmployeeOverview.jsx'
import BusinessDashboard from './BusinessDashboard.jsx'
import Payments from './Payments.jsx'
import { HOME, NAV, ROLE_META } from '../roles.js'
import { go, useRoute } from '../router.js'

// Signed-in shell. The role decides the navigation and which pages exist;
// anything outside the role's list redirects to that role's home.
export default function Workspace({ user, onLogout }) {
  const [expenses, setExpenses] = useState([])
  const [modal, setModal] = useState(null)
  const [toast, setToast] = useState('')
  const route = useRoute()

  const nav = NAV[user.role] || NAV.employee
  const current = nav.find((item) => item.path === route)
  useEffect(() => {
    if (!current) go(HOME[user.role] || HOME.employee)
  }, [current, user.role])

  function refresh(message = '') {
    api('/expenses?limit=100')
      .then(setExpenses)
      .catch((err) => setToast(err.message))
    if (message) setToast(message)
  }
  useEffect(refresh, [])

  const badges = {
    pending: expenses.filter((e) => e.status === 'submitted').length,
    payable: expenses.filter((e) => e.status === 'approved').length,
  }
  const open = (expense) => setModal({ type: 'detail', expense })

  function exportCsv() {
    const esc = (v) => `"${String(v ?? '').replaceAll('"', '""')}"`
    const rows = expenses.map((e) =>
      [e.id, esc(e.owner_name), esc(e.category), e.amount, e.status, e.created_at, esc(e.description)].join(',')
    )
    const csv = ['id,submitted_by,category,amount,status,created_at,description', ...rows].join('\n')
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    link.download = 'passbook-expenses.csv'
    link.click()
    setToast('CSV exported.')
  }

  function page() {
    switch (current?.id) {
      case 'overview':
        return <EmployeeOverview user={user} expenses={expenses} onNew={() => setModal({ type: 'form' })} onOpen={open} />
      case 'my-expenses':
        return (
          <>
            <PageHead title="My expenses" subtitle="Everything you have filed, from draft to reimbursement.">
              <button className="btn btn-primary" onClick={() => setModal({ type: 'form' })}>
                New expense
              </button>
            </PageHead>
            <ExpenseBrowser
              title="My requests"
              statuses={['all', 'draft', 'submitted', 'approved', 'reimbursed', 'rejected']}
              expenses={expenses}
              onOpen={open}
              emptyText="Create your first expense to get started."
            />
          </>
        )
      case 'dashboard':
        return <BusinessDashboard notify={setToast} />
      case 'queue':
        return (
          <>
            <PageHead title="Approval queue" subtitle="Requests from your team waiting on a decision." />
            <ApprovalQueue expenses={expenses} onOpen={open} onRefresh={() => refresh()} notify={setToast} />
          </>
        )
      case 'payments':
        return <Payments expenses={expenses} onOpen={open} onRefresh={refresh} notify={setToast} />
      case 'all':
        return (
          <>
            <PageHead title="All expenses" subtitle="Every expense across the business.">
              <button className="btn btn-ghost" onClick={exportCsv}>
                Export CSV
              </button>
            </PageHead>
            <ExpenseBrowser
              title="Business expenses"
              showOwner
              statuses={['all', 'submitted', 'approved', 'reimbursed', 'rejected']}
              expenses={expenses.filter((e) => e.status !== 'draft')}
              onOpen={open}
            />
          </>
        )
      case 'people':
        return (
          <>
            <PageHead title="People & roles" subtitle="Decide who files, reviews and pays." />
            <PeoplePanel notify={setToast} />
          </>
        )
      default:
        return null
    }
  }

  return (
    <div className="app-shell" data-role={user.role}>
      <Sidebar user={user} route={route} badges={badges} onLogout={onLogout} />

      <main className="main">
        <header className="topbar">
          <span className="crumb">
            {ROLE_META[user.role]?.label} <strong>{current?.label}</strong>
          </span>
          <button className="btn btn-ghost" onClick={() => refresh('Data refreshed.')}>
            Refresh
          </button>
        </header>
        <section className="content">{page()}</section>
      </main>

      <Toast message={toast} onClose={() => setToast('')} />

      {modal?.type === 'form' && user.role === 'employee' && (
        <ExpenseFormModal onClose={() => setModal(null)} onSaved={(msg) => { setModal(null); refresh(msg) }} />
      )}
      {modal?.type === 'detail' && (
        <ExpenseDetailModal
          expense={modal.expense}
          user={user}
          onClose={() => setModal(null)}
          onRefresh={refresh}
          notify={setToast}
        />
      )}
    </div>
  )
}
