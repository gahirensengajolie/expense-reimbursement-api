import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Metric, PageHead } from '../components/ui.jsx'
import { money, titleCase } from '../format.js'
import { go } from '../router.js'

// Manager / admin view: how is money moving across the whole business.
export default function BusinessDashboard({ notify }) {
  const [data, setData] = useState(null)

  function load() {
    api('/expenses/summary')
      .then(setData)
      .catch((err) => notify(err.message))
  }
  useEffect(load, [])

  if (!data) return <div className="muted">Loading spending data…</div>

  const maxMonth = Math.max(1, ...data.by_month.map((m) => m.total))
  const maxCat = Math.max(1, ...data.by_category.map((c) => c.total))
  const maxSpender = Math.max(1, ...data.top_spenders.map((s) => s.total))
  const pipeline = [
    { label: 'In review', value: data.pending_amount, cls: 'seg-review' },
    { label: 'Approved, unpaid', value: data.awaiting_payment_amount, cls: 'seg-approved' },
    { label: 'Reimbursed', value: data.reimbursed_amount, cls: 'seg-paid' },
  ]
  const pipelineTotal = pipeline.reduce((t, p) => t + p.value, 0)

  return (
    <>
      <PageHead title="Spending dashboard" subtitle="How business expenses are moving, across everyone.">
        <button className="btn btn-ghost" onClick={load}>
          Refresh
        </button>
      </PageHead>

      <div className="metric-grid">
        <Metric label="Total spend" value={money(data.total_requested)} hint={`${data.total_count} expenses`} />
        <Metric label="Awaiting review" value={money(data.pending_amount)} hint={`${data.pending_count} requests`} tone="flagged" />
        <Metric label="Approved, unpaid" value={money(data.awaiting_payment_amount)} hint={`${data.awaiting_payment_count} requests`} tone="verified" />
        <Metric label="Reimbursed" value={money(data.reimbursed_amount)} hint={`${data.reimbursed_count} requests`} tone="verified" />
        <Metric label="Approval rate" value={data.approval_rate == null ? '—' : `${data.approval_rate}%`} hint={`${data.rejected_count} rejected`} />
        <Metric label="Average expense" value={money(data.average_expense)} />
        <Metric label="Policy flags" value={data.flagged_count} hint="over category limit" tone="alert" />
        <button className="metric metric-action" onClick={() => go('/queue')}>
          <span className="metric-label">Reviewer action</span>
          <strong className="metric-value">Open queue →</strong>
        </button>
      </div>

      <div className="dash-grid">
        <section className="card">
          <div className="card-head">
            <div className="section-heading">Spend by month</div>
            <span className="muted">Last {data.by_month.length} months</span>
          </div>
          <div className="bar-chart" role="img" aria-label="Monthly spend">
            {data.by_month.map((m) => (
              <div className="bar-col" key={m.month} title={`${m.label}: ${money(m.total)} (${m.count})`}>
                <span className="bar-value">{m.total ? money(m.total).replace(/\.00$/, '') : ''}</span>
                <div className="bar" style={{ height: `${(m.total / maxMonth) * 100}%` }} />
                <span className="bar-label">{m.label}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-head">
            <div className="section-heading">Where the money goes</div>
          </div>
          <div className="hbar-list">
            {data.by_category.length ? (
              data.by_category.map((c) => (
                <HBar key={c.category} label={titleCase(c.category)} value={c.total} max={maxCat} sub={`${c.count}`} />
              ))
            ) : (
              <div className="empty-state"><strong>No spend recorded yet.</strong></div>
            )}
          </div>
        </section>

        <section className="card">
          <div className="card-head">
            <div className="section-heading">Approval pipeline</div>
          </div>
          <div className="pipeline">
            <div className="segbar">
              {pipeline.map((p) =>
                p.value > 0 ? (
                  <div key={p.label} className={p.cls} style={{ flex: p.value }} title={`${p.label}: ${money(p.value)}`} />
                ) : null
              )}
              {pipelineTotal === 0 && <div className="seg-empty" style={{ flex: 1 }} />}
            </div>
            <div className="legend">
              {pipeline.map((p) => (
                <div key={p.label}>
                  <i className={p.cls} /> {p.label} <strong>{money(p.value)}</strong>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-head">
            <div className="section-heading">Top spenders</div>
          </div>
          <div className="hbar-list">
            {data.top_spenders.length ? (
              data.top_spenders.map((s) => (
                <HBar key={s.owner_id} label={s.full_name} value={s.total} max={maxSpender} sub={`${s.count}`} />
              ))
            ) : (
              <div className="empty-state"><strong>No submitted expenses yet.</strong></div>
            )}
          </div>
        </section>
      </div>
    </>
  )
}

function HBar({ label, value, max, sub }) {
  return (
    <div className="hbar">
      <div className="hbar-row">
        <span>{label} <small className="muted">· {sub}</small></span>
        <strong>{money(value)}</strong>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${(value / max) * 100}%` }} />
      </div>
    </div>
  )
}
