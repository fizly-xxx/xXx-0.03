# Contributing Guidelines

## Testing & Bug Fix Requirements

### UI Checkbox & Toggle Issues
- **Problem**: Checkboxes connected to complex state (StatTrak selector) fail when:
  - Using inline `onchange` handlers without proper event listener backup
  - CSS selector for `:checked` state doesn't trigger visual updates
  - No forced re-render after state change in JavaScript objects

- **Solution**:
  1. Always attach explicit event listeners in `attachAutoSaveListeners()` for complex state inputs
  2. Verify CSS `:checked` selector path: `.toggle-switch input:checked ~ .toggle-track` (use sibling combinator `~`, not child)
  3. Force update dependent UI elements when checkbox changes, not just update internal state

### Item Rendering in Grids
- **Requirements**:
  1. Always check for empty arrays before rendering: `if (!items || items.length === 0)`
  2. Show placeholder message when grid is empty
  3. Validate all item properties exist before rendering (use fallbacks like `item.name || 'Unknown'`)
  4. Log rendered count for debugging

### Sales/Inventory Functionality
- **Requirements**:
  1. `loadInventory()` and `loadSales()` must verify `pywebview.api` and `handshake` before executing
  2. All grid rendering must handle API response validation
  3. Sell operations must pass proper item ID type (number if API expects int)
  4. Modal dialogs must show before attempting operations

### Initialization Order
- **Correct order**: `DOMContentLoaded` ? `attachAutoSaveListeners()` ? bind checkboxes ? `pywebviewready` ? `initWeapons()` ? `loadConfig()`
- **Do not** call `updateSniperTarget()` before `currentWeaponSkinsGrouped` is populated

## Code Quality Standards

- Use `addLog()` for all important state changes and errors
- Always wrap async operations in try/catch
- Never suppress error messages—log them for debugging
- Validate element existence before manipulating: `if (!element) return;`
- Use `?.` optional chaining for DOM queries that might fail