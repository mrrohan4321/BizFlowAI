# 🧱 components/

`UI.jsx` holds the small shared building blocks used by every page.

| Export | Purpose |
|---|---|
| `money(value)`, `dateText(value)`, `today()` | INR formatting, date display, today's date |
| `Status` | status badge (unpaid / partially_paid / paid, needs review) |
| `PageHead`, `Panel`, `Stat` | page header, card container, summary number card |
| `Loading`, `Empty`, `ErrorBox` | loading, empty and error states (`ErrorBox` shows the friendly API message) |
| `Modal`, `Field` | dialog and labelled form field |
| `Warnings` | list of validation warnings returned by the extraction/confirm API |
| `LinkArrow` | small "go to" link |

Rule: components display values from the API. They never calculate balances, status, overdue days or forecasts.
