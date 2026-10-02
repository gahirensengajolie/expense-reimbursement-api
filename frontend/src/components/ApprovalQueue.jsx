import { api } from '../api.js'
import { money, formatDate, titleCase } from '../format.js'

export default function ApprovalQueue({ expenses, onOpen, onRefresh, notify }) {
  const queue = expenses.filter((item) => item.status === 'submitted')

  async function review(expense, approve) {
    const comment = window.prompt(approve ? 'Optional approval comment:' : 'Reason for rejection:') || ''
    if (!approve && !comment.trim()) {
      notify('Add a reason before rejecting an expense.')
      return
    }
    try {
      await api(`/expenses/${expense.id}/review`, {
        method: 'POST',
        body: JSON.stringify({ approve, comment }),
      })
      notify(approve ? 'Expense approved.' : 'Expense rejected.')
      onRefresh()
    } catch (err) {
      notify(err.message)
    }
  }

  return (
    <section className="card" id="queue">
      <div className="card-head">
        <div>
          <div className="section-heading">Approval queue</div>
          <p className="card-subtitle">Expenses submitted by your team, waiting on a decision.</p>
        </div>
        <span className="pending-count">{queue.length} pending</span>
      </div>

      {queue.length ? (
        <div className="queue-list">
          {queue.map((item) => (
            <div className="queue-row" key={item.id}>
              <div className="queue-main">
                <strong>
                  {item.owner_name || 'Employee'} — {titleCase(item.category)}
                  {item.policy_flagged && <span className="flag-mark">over limit</span>}
                </strong>
                <small>
                  {item.description || 'No description'} — submitted {formatDate(item.created_at)}
                </small>
              </div>
              <div className="queue-amount">{money(item.amount)}</div>
              <div className="queue-actions">
                <button className="btn btn-ghost btn-compact" onClick={() => onOpen(item)}>
                  View
                </button>
                <button className="btn btn-danger btn-compact" onClick={() => review(item, false)}>
                  Reject
                </button>
                <button className="btn btn-primary btn-compact" onClick={() => review(item, true)}>
                  Approve
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <strong>Nothing waiting for review.</strong>
          <p>Submitted expenses will appear here.</p>
        </div>
      )}
    </section>
  )
}
