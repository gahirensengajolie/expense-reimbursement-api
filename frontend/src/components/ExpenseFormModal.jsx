import { useState } from 'react'
import { api } from '../api.js'
import { Field, Modal } from './ui.jsx'
import { CATEGORIES } from '../format.js'

export default function ExpenseFormModal({ expense, onClose, onSaved }) {
  const [form, setForm] = useState({
    category: expense?.category || '',
    amount: expense?.amount || '',
    description: expense?.description || '',
  })
  const [error, setError] = useState('')

  async function save(event) {
    event.preventDefault()
    setError('')
    try {
      await api(expense ? `/expenses/${expense.id}` : '/expenses', {
        method: expense ? 'PATCH' : 'POST',
        body: JSON.stringify({ ...form, amount: Number(form.amount) }),
      })
      onSaved(expense ? 'Draft updated.' : 'Draft created.')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Modal title={expense ? 'Edit draft' : 'New expense'} onClose={onClose}>
      <form onSubmit={save}>
        <Field label="Category">
          <select
            required
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          >
            <option value="">Choose a category</option>
            {CATEGORIES.map((category) => (
              <option key={category}>{category}</option>
            ))}
          </select>
        </Field>

        <Field label="Amount (USD)">
          <input
            required
            min="0.01"
            step="0.01"
            type="number"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            placeholder="0.00"
          />
        </Field>

        <Field label="What was this for?">
          <textarea
            rows="4"
            maxLength="1000"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Add context for your reviewer"
          />
        </Field>

        {error && <div className="form-error">{error}</div>}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary">{expense ? 'Save changes' : 'Create draft'}</button>
        </div>
      </form>
    </Modal>
  )
}
