import { useEffect, useState } from 'react'
import { api, download } from '../api.js'
import Sidebar from '../components/Sidebar.jsx'
import ApprovalQueue from '../components/ApprovalQueue.jsx'
import PeoplePanel from '../components/PeoplePanel.jsx'
import ExpenseBrowser from '../components/ExpenseBrowser.jsx'
import ExpenseFormModal from '../components/ExpenseFormModal.jsx'
import ExpenseDetailModal from '../components/ExpenseDetailModal.jsx'
import ChangePasswordModal from '../components/ChangePasswordModal.jsx'
import { Toast, PageHead } from '../components/ui.jsx'
import EmployeeOverview from './EmployeeOverview.jsx'
import BusinessDashboard from './BusinessDashboard.jsx'
import Payments from './Payments.jsx'
import { HOME, NAV, ROLE_META, isReviewer } from '../roles.js'
import { go, useRoute } from '../router.js'

// Signed-in shell. The role decides the navigation and which pages exist;
// anything outside the role's list redirects to that role's home.
const PAGE_SIZE = 100

export default function Workspace({ user, onLogout, onUserChanged }) {
  const [expenses, setExpenses] = useState([])
  const [hasMore, setHasMore] = useState(false)
  // Reviewer lists/badges come from the server so they stay correct beyond the first page.
  const [queueItems, setQueueItems] = useState([])
  const [payableItems, setPayableItems] = useState([])
  const [counts, setCounts] = useState({ pending: 0, payable: 0 })
  const [modal, setModal] = useState(null)
  const [toast, setToast] = useState('')
  const route = useRoute()

  const nav = NAV[user.role] || NAV.employee
  const current = nav.find((item) => item.path === route)
  useEffect(() => {
    if (!current) go(HOME[user.role] || HOME.employee)
  }, [current, user.role])

  function refresh(message = '') {
    api(`/expenses?limit=${PAGE_SIZE}`)
      .then((items) => {
        setExpenses(items)
        setHasMore(items.length === PAGE_SIZE)
      })
      .catch((err) => setToast(err.message))
    if (isReviewer(user)) {
      api('/expenses/counts').then(setCounts).catch(() => {})
      api(`/expenses?status=submitted&limit=${PAGE_SIZE}`).then(setQueueItems).catch(() => {})
      if (user.role === 'admin') {
        api(`/expenses?status=approved&limit=${PAGE_SIZE}`).then(setPayableItems).catch(() => {})
      }
    }
    if (message) setToast(message)
  }
  useEffect(refresh, [])

  // Append the next page; the offset is how many rows we already hold.
  function loadMore() {
    api(`/expenses?limit=${PAGE_SIZE}&offset=${expenses.length}`)
      .then((items) => {
        setExpenses((current) => [...current, ...items])
        setHasMore(items.length === PAGE_SIZE)
      })
      .catch((err) => setToast(err.message))
  }

  const badges = { pending: counts.pending, payable: counts.payable }
  const open = (expense) => setModal({ type: 'detail', expense })

  async function exportCsv() {
    try {
      await download('/expenses/export', 'passbook-expenses.csv')
      setToast('CSV exported.')
    } catch (err) {
      setToast(err.message)
    }
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
              hasMore={hasMore}
              onLoadMore={loadMore}
            />
          </>
        )
      case 'dashboard':
        return <BusinessDashboard user={user} notify={setToast} />
      case 'queue':
        return (
          <>
            <PageHead title="Approval queue" subtitle={user.role === 'manager' ? 'Requests from your team waiting on a decision.' : 'Requests across the business waiting on a decision.'} />
            <ApprovalQueue expenses={queueItems} onOpen={open} onRefresh={() => refresh()} notify={setToast} />
          </>
        )
      case 'payments':
        return <Payments expenses={payableItems} onOpen={open} onRefresh={refresh} notify={setToast} />
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
              hasMore={hasMore}
              onLoadMore={loadMore}
            />
          </>
        )
      case 'people':
        return (
          <>
            <PageHead title="People & roles" subtitle="Decide who files, reviews and pays." />
            <PeoplePanel notify={setToast} me={user} />
          </>
        )
      default:
        return null
    }
  }

  return (
    <div className="app-shell" data-role={user.role}>
      <Sidebar
        user={user}
        route={route}
        badges={badges}
        onLogout={onLogout}
        onChangePassword={() => setModal({ type: 'password' })}
      />

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
      {(user.must_change_password || modal?.type === 'password') && (
        <ChangePasswordModal
          required={user.must_change_password}
          onClose={() => setModal(null)}
          onDone={(message) => {
            setModal(null)
            setToast(message)
            onUserChanged()
          }}
        />
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
