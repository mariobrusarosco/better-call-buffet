## timeline_status - The Background Job Tracker

_The Problem:_
Remember when we discussed adding a transaction for Jan 2nd today? That requires
recalculating 285+ days of balances in the background!

_The Solution:_
timeline_status = Column(String, default="current")

_Three states:_

- "current" ✅ - Balance is accurate, up-to-date
- "updating" 🔄 - Background job is recalculating this balance
- "failed" ❌ - Recalculation failed, needs attention

_Real-world flow:_

1. User adds transaction for Jan 2nd
2. Mark Jan 2nd → Today as "updating"
3. User requests timeline → Show "⏳ Balance timeline updating..."
4. Background job finishes → Mark as "current"
5. User refreshes → See accurate balances

# has_transactions - The Gap Filler Flag

The Problem:
User has transactions on:

- Oct 1st: -$500
- Oct 15th: +$200

What about Oct 2nd-14th? No transactions, but you still need daily balances!

The Solution:
has_transactions = Column(Boolean, default=False)

Two types of balance points:

Real (has_transactions = True):
Oct 1st: $1000 - $500 = $500 ✅ Real transaction happened

Cloned (has_transactions = False):
Oct 2nd: $500 (cloned from Oct 1st) 📋 No transaction, just maintaining timeline
Oct 3rd: $500 (cloned from Oct 2nd) 📋
...
Oct 14th: $500 (cloned from Oct 13th) 📋

Why track this?

- Performance: Skip recalculating cloned days when transactions change
- Debugging: Know which balances came from real vs filled gaps
- Optimization: Delete unnecessary cloned points if needed

Example scenario:
User adds transaction for Oct 5th → Only recalculate Oct 5th-14th
Don't waste time recalculating Oct 2nd-4th (they're just clones from Oct 1st)

---

Visual Summary

Timeline for October:
┌─────────────────────────────────────────────────┐
│ Oct 1: $500 [has_transactions=True, status=current] ← Real transaction
│ Oct 2: $500 [has_transactions=False, status=current] ← Cloned (gap fill)
│ Oct 3: $500 [has_transactions=False, status=current] ← Cloned (gap fill)
│ Oct 4: $500 [has_transactions=False, status=updating] ← Being recalculated
│ Oct 5: $700 [has_transactions=True, status=updating] ← New transaction added
└─────────────────────────────────────────────────┘

---
