# Veritas UI/UX Improvement Suggestions

## Context

This document captures UI/UX improvements to differentiate Veritas from a generic dashboard pattern and better showcase its value proposition for the demo and case study.

**Target Outcome:** A demo-ready UI that clearly communicates:
- The speed advantage (48 hours → 4 seconds)
- The explainable ML risk scoring (SHAP contributions)
- The compliance workflow (approve/review/reject decisions)

---

## Current State

The current UI uses a professional but generic dashboard pattern:
- Gray/white color scheme
- Standard card layouts
- Minimal visual hierarchy

This works but doesn't differentiate Veritas or highlight its key value propositions.

---

## Priority Improvements

### P1: Results Page - Risk Visualization

**Problem:** The SHAP-based risk explanations are Veritas's key differentiator, but they're currently displayed as a simple list in a card.

**Suggestions:**
1. **Horizontal bar chart for feature contributions**
   - Green bars for risk-reducing factors (pointing left)
   - Red bars for risk-increasing factors (pointing right)
   - Makes the ML explainability visually intuitive

2. **Risk score gauge/dial**
   - Visual representation of 0-1 score
   - Color gradient from green → amber → red
   - Clear tier boundaries marked (Low < 0.3, Medium < 0.7, High)

3. **Decision prominence**
   - Make the recommendation (Approve/Review/Reject) more visually prominent
   - Full-width banner at top of results with color coding
   - Large, clear CTA for taking action

### P2: Dashboard - Processing Speed Highlight

**Problem:** The 4-second processing time is buried. This is a key selling point.

**Suggestions:**
1. **Live processing timer on upload**
   - Show real-time seconds counter during processing
   - Display final time prominently: "Processed in 3.8 seconds"
   - Compare to manual: "vs. 48 hours manual review"

2. **Stats cards enhancement**
   - Add "Average Processing Time" as a prominent stat
   - Show time saved calculation: "X hours saved this month"

### P3: Workflow Clarity

**Problem:** Current UI is document-centric but KYC is decision-centric.

**Suggestions:**
1. **Status-based views**
   - Tab navigation: Pending | In Review | Approved | Rejected
   - Queue-style list for compliance officers to work through

2. **Batch processing UX**
   - Progress indicator for batch jobs
   - Summary view: "45 Approved, 3 Review, 2 Rejected"
   - One-click bulk actions for low-risk approvals

### P4: Landing Page for Case Study

**Problem:** Current landing page is functional but not optimized for case study visitors.

**Suggestions:**
1. **Hero section**
   - Animated comparison: Manual (48 hrs) vs Veritas (4 sec)
   - Screenshot/video preview of the dashboard
   - Clear CTA: "Try the Demo" / "Book a Pilot"

2. **Social proof section**
   - Placeholder for pilot testimonials
   - "Built for cross-border payments companies"
   - Target company logos (if permitted)

3. **How it works**
   - 3-step visual: Upload → Process → Decision
   - Each step with timing and what happens

---

## Visual Identity Suggestions

### Color Refinements

Current: Generic gray/white
Suggested additions:
- **Trust blue** (#2563EB) - For primary actions, trust signals
- **Success green** (#16A34A) - Approved states, positive factors
- **Warning amber** (#D97706) - Review states, attention needed
- **Alert red** (#DC2626) - Rejected states, risk factors

### Typography Hierarchy

- **Decisions/Recommendations:** Large, bold, color-coded
- **Risk scores:** Prominent with visual indicator
- **Processing times:** Highlighted with comparison context
- **Extracted data:** Clean, scannable tables

### Iconography

Consider custom icons for:
- Document types (passport, utility bill, business doc)
- Risk tiers (shield variations)
- Screening status (sanctions, adverse media)

---

## Demo-Specific Considerations

For the 3-minute demo video (per PRD):

1. **Minute 1 (Problem):** Landing page should set this up
2. **Minute 2 (Solution):** Upload → Processing → Results flow should be smooth and visually clear
3. **Minute 3 (Results):** ROI calculator and comparison should be prominent

**Key moments to optimize:**
- File drop animation (satisfying feedback)
- Processing spinner with timer
- Results reveal (possibly animate in)
- Risk tier badge appearance

---

## Implementation Notes

These improvements are **not blockers** for the initial demo/deployment. They're enhancements to consider after:
1. Deployment is complete
2. Basic demo flow is verified working
3. Case study page is live

Estimated effort:
- P1 (Risk visualization): 2-3 hours
- P2 (Speed highlight): 1-2 hours
- P3 (Workflow clarity): 3-4 hours
- P4 (Landing page): 2-3 hours

---

## References

- [PRD Demo Script](./veritas-prd.md#demo-script-3-minutes)
- [PRD One-Pager Content](./veritas-prd.md#one-pager-content)
- Current shadcn/ui components: Card, Badge, Table, Alert
