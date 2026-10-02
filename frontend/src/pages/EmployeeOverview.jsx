import { Metric, PageHead, StatusTag } from '../components/ui.jsx'
import { money, formatDate, titleCase } from '../format.js'

// Employee home: what do I still need to do, and what happened to my requests.
export default function EmployeeOverview({ user, expenses, onNew, onOpen }) {
  const sum = (status) => expenses.filter((e) => e.status === status).reduce((t, e) => t + e.amount, 0)
  const count = (status) => expenses.filter((e) => e.status === status).length
  const attention = expenses.filter((e) => e.status === 'draft' || e.status === 'rejected')
  const recent = expenses.filter((e) => e.status !== 'draft').slice(0, 5)

  return (
    <>
      <PageHead title={`Hi ${user.full_name.split(' ')[0]}.`} subtitle="Your expense requests and what needs you next.">
        <button className="btn btn-primary" onClick={onNew}>
          New expense
        </button>
      </PageHead>

      <div className="metric-grid">
        <Metric label="Drafts to submit" value={count('draft')} tone="neutral" />
        <Metric label="Waiting for review" value={money(sum('submitted'))} hint={`${count('submitted')} requests`} tone="flagged" />
        <Metric label="Approved, awaiting payment" value={money(sum('approved'))} hint={`${count('approved')} requests`} tone="verified" />
        <Metric label="Paid back to you" value={money(sum('reimbursed'))} hint={`${count('reimbursed')} requests`} tone="verified" />
      </div>

      <div className="dash-grid">
        <section className="card">
          <div className="card-head">
            <div>
              <div className="section-heading">Needs your attention</div>
              <p className="card-subtitle">Drafts to submit and rejected requests to fix.</p>
            </div>
          </div>
          <MiniList items={attention} onOpen={onOpen} empty="You're all caught up." />
        </section>

        <section className="card">
          <div className="card-head">
            <div>
              <div className="section-heading">Recent activity</div>
              <p className="card-subtitle">Your latest submitted requests.</p>
            </div>
          </div>
          <MiniList items={recent} onOpen={onOpen} empty="Nothing submitted yet." />
        </section>
      </div>
    </>
  )
}

function MiniList({ items, onOpen, empty }) {
  if (!items.length)
    return (
      <div className="empty-state">
        <strong>{empty}</strong>
      </div>
    )
  return (
    <div className="mini-list">
      {items.map((item) => (
        <button className="mini-row" key={item.id} onClick={() => onOpen(item)}>
          <span className="mini-main">
            <strong>{titleCase(item.category)}</strong>
            <small>
              {formatDate(item.created_at)}
              {item.status === 'rejected' && item.reviewer_comment ? ` — ${item.reviewer_comment}` : ''}
            </small>
          </span>
          <StatusTag status={item.status} />
          <span className="amount-cell">{money(item.amount)}</span>
        </button>
      ))}
    </div>
  )
}
