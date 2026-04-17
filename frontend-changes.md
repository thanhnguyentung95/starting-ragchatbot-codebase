# Frontend Changes — Theme Toggle Button

## Feature
Dark/light mode toggle button positioned fixed in the top-right corner.

## Files Modified

### `frontend/index.html`
- Bumped CSS version to `?v=11` and JS version to `?v=10`
- Added `#themeToggle` button (fixed top-right) with inline sun + moon SVG icons
- Button uses `aria-label` for accessibility; icons carry `aria-hidden="true"`

### `frontend/style.css`
- Added `[data-theme="light"]` CSS variable overrides (background, surface, text, border, shadow)
- Added `transition` on `body` for smooth 0.3s color/background change on toggle
- Added `.theme-toggle` styles: fixed position, 42×42px circle, surface background, border, shadow
- Hover: scale(1.1) + 15deg rotation + blue border/shadow accent
- Focus: 3px focus ring using `--focus-ring` variable (keyboard accessible)
- Icon visibility: `.icon-sun` shown by default (dark mode); swapped to `.icon-moon` when `[data-theme="light"]`

### `frontend/script.js`
- Added `currentTheme` global state and `themeToggle` DOM ref
- Added `initTheme()` — reads `localStorage.theme`, falls back to `'dark'`, applies on load
- Added `applyTheme(theme)` — sets `data-theme` attribute on body, persists to localStorage, updates `aria-label`
- Added `toggleTheme()` — flips between dark/light
- `setupEventListeners()` now binds click + keyboard (Enter/Space) on `#themeToggle`
- `initTheme()` called in `DOMContentLoaded` before other setup

## Behaviour
- Default theme: dark (unchanged appearance for new users)
- Theme persisted in `localStorage` key `theme` across sessions
- Button keyboard-navigable (Tab to focus, Enter or Space to activate)
- Smooth CSS transitions on background/color changes (0.3s ease)
- Hover animation: slight scale + rotation gives clear interactive feedback
