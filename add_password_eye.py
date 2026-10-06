"""Adds a show/hide (eye) button to every password field.
Run from the project root:  python3 add_password_eye.py
Safe to run twice: it skips files that are already changed."""
import re
from pathlib import Path

SRC = Path("frontend/src")

COMPONENT = '''
// Password field with a show/hide (eye) button. Takes the same props as <input>.
export function PasswordInput(props) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="password-wrap">
      <input {...props} type={visible ? 'text' : 'password'} />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        title={visible ? 'Hide password' : 'Show password'}
      >
        {visible ? (
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  )
}
'''

CSS = '''
/* Password show/hide button */
.password-wrap { position: relative; }
.password-wrap input { width: 100%; padding-right: 46px; box-sizing: border-box; }
.password-toggle {
  position: absolute; right: 4px; top: 50%; transform: translateY(-50%);
  width: 38px; height: 38px; display: grid; place-items: center;
  border: 0; background: transparent; color: var(--ink-soft); cursor: pointer; border-radius: 8px;
}
.password-toggle:hover { color: var(--ink); }
.password-toggle:focus-visible { outline: 2px solid currentColor; outline-offset: 1px; }
'''


def convert_inputs(text):
    """Turn every <input ... type="password" ... /> into <PasswordInput ... />."""
    count = 0

    def fix(m):
        nonlocal count
        block = m.group(0)
        if 'type="password"' not in block:
            return block
        count += 1
        block = block.replace("<input", "<PasswordInput", 1)
        return re.sub(r'\n[ \t]*type="password"', "", block, count=1)

    return re.sub(r"<input\b(?:(?!/>).)*/>", fix, text, flags=re.S), count


def edit(path, fn):
    p = SRC / path
    new = fn(p.read_text())
    p.write_text(new)


# 1. the component
ui = (SRC / "components/ui.jsx").read_text()
if "export function PasswordInput" not in ui:
    ui = ui.replace("import { useEffect } from 'react'", "import { useEffect, useState } from 'react'", 1)
    ui = ui.rstrip("\n") + "\n" + COMPONENT
    (SRC / "components/ui.jsx").write_text(ui)
    print("ui.jsx: added PasswordInput")

# 2. sign-in / sign-up page
def auth(t):
    t, n = convert_inputs(t)
    t = t.replace("import { Field } from '../components/ui.jsx'",
                  "import { Field, PasswordInput } from '../components/ui.jsx'", 1)
    if "autoComplete={mode" not in t:
        t = t.replace('<PasswordInput\n              required\n              minLength="8"',
                      '<PasswordInput\n              required\n              minLength="8"\n'
                      "              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}", 1)
    print(f"Auth.jsx: {n} password field(s) converted")
    return t
edit("pages/Auth.jsx", auth)

# 3. change-password dialog
def modal(t):
    t, n = convert_inputs(t)
    t = t.replace("import { Field, Modal } from './ui.jsx'",
                  "import { Field, Modal, PasswordInput } from './ui.jsx'", 1)
    print(f"ChangePasswordModal.jsx: {n} password field(s) converted")
    return t
edit("components/ChangePasswordModal.jsx", modal)

# 4. styles
css = (SRC / "styles.css").read_text()
if ".password-toggle" not in css:
    (SRC / "styles.css").write_text(css.rstrip("\n") + "\n" + CSS)
    print("styles.css: added eye-button styles")
print("Done.")
