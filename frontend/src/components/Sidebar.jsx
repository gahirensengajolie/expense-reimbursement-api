import { initials } from '../format.js'
import { NAV, ROLE_META } from '../roles.js'

export default function Sidebar({ user, route, badges, onLogout }) {
  const items = NAV[user.role] || []
  const sections = [...new Set(items.map((item) => item.section))]
  const meta = ROLE_META[user.role]

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="wordmark">Passbook</div>
        <span className="role-badge">{meta.label}</span>
      </div>

      <nav aria-label="Main navigation">
        {sections.map((section) => (
          <div className="nav-section" key={section}>
            <div className="nav-label">{section}</div>
            {items
              .filter((item) => item.section === section)
              .map((item) => (
                <a
                  key={item.id}
                  href={`#${item.path}`}
                  className={`nav-item ${route === item.path ? 'active' : ''}`}
                  aria-current={route === item.path ? 'page' : undefined}
                >
                  {item.label}
                  {badges[item.badge] > 0 && <span className="nav-count">{badges[item.badge]}</span>}
                </a>
              ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="profile">
          <span className="avatar">{initials(user.full_name)}</span>
          <div>
            <strong>{user.full_name}</strong>
            <small>{meta.tagline}</small>
          </div>
        </div>
        <button className="link-btn" onClick={onLogout}>
          Sign out
        </button>
      </div>
    </aside>
  )
}
