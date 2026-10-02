import { useMemo, useState } from 'react'
import { StatusTag } from './ui.jsx'
import { STATUSES, money, formatDate, titleCase } from '../format.js'

// Filterable expense table. `showOwner` adds a "Submitted by" column for
// reviewers; employees only ever see their own rows so they don't need it.
export default function ExpenseBrowser({ expenses, showOwner, onOpen, title, statuses = STATUSES, emptyText }) {
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  const visible = useMemo(() => {
    const term = search.toLowerCase()
    return expenses
      .filter((item) => filter === 'all' || item.status === filter)
      .filter((item) =>
        `${item.category} ${item.description} ${item.owner_name || ''}`.toLowerCase().includes(term)
      )
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  }, [expenses, filter, search])

  return (
    <section className="card">
      <div className="card-head">
        <div className="section-heading">{title}</div>
        <span className="muted">{visible.length} records</span>
      </div>

      <div className="filters">
        {statuses.map((status) => (
          <button
            key={status}
            className={`chip ${filter === status ? 'chip-active' : ''}`}
            onClick={() => setFilter(status)}
          >
            {status === 'all' ? 'All' : titleCase(status)}
          </button>
        ))}
        <input
          className="search-input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={showOwner ? 'Search by person, category…' : 'Search expenses'}
        />
      </div>

      <div className="table-wrap">
        <table className="ledger-table">
          <thead>
            <tr>
              <th>Expense</th>
              {showOwner && <th>Submitted by</th>}
              <th>Amount</th>
              <th>Status</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {visible.length ? (
              visible.map((item) => (
                <tr key={item.id} className={`row-status-${item.status}`} onClick={() => onOpen(item)}>
                  <td>
                    <strong>{titleCase(item.category)}</strong>
                    {item.policy_flagged && <span className="flag-mark">over limit</span>}
                    <small>{item.description || 'No description'}</small>
                  </td>
                  {showOwner && <td>{item.owner_name || '—'}</td>}
                  <td className="amount-cell">{money(item.amount)}</td>
                  <td>
                    <StatusTag status={item.status} />
                  </td>
                  <td className="muted amount-cell">{formatDate(item.created_at)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={showOwner ? 5 : 4}>
                  <div className="empty-state">
                    <strong>No expenses here.</strong>
                    <p>{emptyText || 'Try a different filter.'}</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
