import { api } from '../api.js'
import { PageHead } from '../components/ui.jsx'
import { money, formatDate, titleCase } from '../format.js'

// Admin-only: approved expenses waiting to be paid back.
export default function Payments({ expenses, onOpen, onRefresh, notify }) {
  const payable = expenses.filter((e) => e.status === 'approved')
  const total = payable.reduce((t, e) => t + e.amount, 0)

  async function pay(expense) {
    try {
      await api(`/expenses/${expense.id}/reimburse`, { method: 'POST' })
      onRefresh(`Marked ${money(expense.amount)} as reimbursed.`)
    } catch (err) {
      notify(err.message)
    }
  }

  return (
    <>
      <PageHead title="Payments" subtitle="Approved expenses that are ready to be reimbursed." />
      <section className="card">
        <div className="card-head">
          <div>
            <div className="section-heading">Ready to pay</div>
            <p className="card-subtitle">{payable.length} approved · {money(total)} total</p>
          </div>
        </div>
        {payable.length ? (
          <div className="queue-list">
            {payable.map((item) => (
              <div className="queue-row" key={item.id}>
                <div className="queue-main">
                  <strong>{item.owner_name || 'Employee'} — {titleCase(item.category)}</strong>
                  <small>{item.description || 'No description'} — filed {formatDate(item.created_at)}</small>
                </div>
                <div className="queue-amount">{money(item.amount)}</div>
                <div className="queue-actions">
                  <button className="btn btn-ghost btn-compact" onClick={() => onOpen(item)}>View</button>
                  <button className="btn btn-primary btn-compact" onClick={() => pay(item)}>Mark reimbursed</button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>Nothing to pay right now.</strong>
            <p>Approved expenses will appear here.</p>
          </div>
        )}
      </section>
    </>
  )
}
