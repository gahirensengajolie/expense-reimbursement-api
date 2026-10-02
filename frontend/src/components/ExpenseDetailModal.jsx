import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Modal, StatusTag } from './ui.jsx'
import { money, formatDate } from '../format.js'

export default function ExpenseDetailModal({ expense, user, onClose, onRefresh, notify }) {
  const [audit, setAudit] = useState([])
  const [comment, setComment] = useState('')

  useEffect(() => {
    api(`/expenses/${expense.id}/audit`)
      .then(setAudit)
      .catch(() => setAudit([]))
  }, [expense.id])

  const isOwner = expense.owner_id === user.id
  const isReviewer = (user.role === 'manager' || user.role === 'admin') && !isOwner

  async function runAction(type) {
    try {
      if (type === 'delete') {
        if (!window.confirm('Delete this draft? This cannot be undone.')) return
        await api(`/expenses/${expense.id}`, { method: 'DELETE' })
      } else if (type === 'submit') {
        await api(`/expenses/${expense.id}/submit`, { method: 'POST' })
      } else if (type === 'resubmit') {
        await api(`/expenses/${expense.id}/resubmit`, { method: 'POST' })
      } else if (type === 'approve' || type === 'reject') {
        await api(`/expenses/${expense.id}/review`, {
          method: 'POST',
          body: JSON.stringify({ approve: type === 'approve', comment }),
        })
      } else if (type === 'reimburse') {
        await api(`/expenses/${expense.id}/reimburse`, { method: 'POST' })
      }
      onClose()
      onRefresh(type === 'delete' ? 'Draft deleted.' : 'Expense updated.')
    } catch (err) {
      notify(err.message)
    }
  }

  const showActionPanel =
    isReviewer ||
    (isOwner && (expense.status === 'draft' || expense.status === 'rejected')) ||
    (user.role === 'admin' && expense.status === 'approved')

  return (
    <Modal title={`Expense #${expense.id} — ${expense.category}`} onClose={onClose}>
      <div className="detail-top">
        <StatusTag status={expense.status} />
        <strong className="detail-amount">{money(expense.amount)}</strong>
      </div>

      <div className="detail-meta">
        {expense.owner_name && (
          <div>
            <small>Submitted by</small>
            <strong>{expense.owner_name}</strong>
          </div>
        )}
        <div>
          <small>Created</small>
          <strong>{formatDate(expense.created_at)}</strong>
        </div>
        <div>
          <small>Category limit</small>
          <strong>{money(expense.policy_limit)}</strong>
        </div>
      </div>

      {expense.policy_flagged && (
        <div className="policy-alert">
          <strong>Over policy limit.</strong> {expense.policy_flag_reason}
        </div>
      )}

      <p className="detail-description">{expense.description || 'No description provided.'}</p>

      <div className="section-heading">History</div>
      <div className="timeline">
        {audit.length ? (
          audit.map((item) => (
            <div className="timeline-item" key={item.id}>
              <strong>{item.action.replaceAll('_', ' ')}</strong>
              <p>
                {formatDate(item.timestamp)}
                {item.comment ? ` — ${item.comment}` : ''}
              </p>
            </div>
          ))
        ) : (
          <span className="muted">No events recorded yet.</span>
        )}
      </div>

      {showActionPanel && (
        <>
          <textarea
            className="comment-box"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={isOwner ? 'Optional note' : 'Optional reviewer comment'}
          />
          <div className="modal-actions">
            {isOwner && expense.status === 'draft' && (
              <>
                <button className="btn btn-danger" onClick={() => runAction('delete')}>
                  Delete
                </button>
                <button className="btn btn-primary" onClick={() => runAction('submit')}>
                  Submit for review
                </button>
              </>
            )}
            {isOwner && expense.status === 'rejected' && (
              <button className="btn btn-primary" onClick={() => runAction('resubmit')}>
                Resubmit
              </button>
            )}
            {isReviewer && expense.status === 'submitted' && (
              <>
                <button className="btn btn-danger" onClick={() => runAction('reject')}>
                  Reject
                </button>
                <button className="btn btn-primary" onClick={() => runAction('approve')}>
                  Approve
                </button>
              </>
            )}
            {user.role === 'admin' && expense.status === 'approved' && (
              <button className="btn btn-primary" onClick={() => runAction('reimburse')}>
                Mark reimbursed
              </button>
            )}
          </div>
        </>
      )}
    </Modal>
  )
}
