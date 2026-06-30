---
name: DevFlow Assistant
description: A precise, dark-first control surface for traceable engineering workflows.
colors:
  canvas: "oklch(0.105 0 0)"
  surface: "oklch(0.145 0.008 110)"
  surface-raised: "oklch(0.185 0.01 110)"
  line: "oklch(0.30 0.012 110)"
  ink: "oklch(0.94 0.006 110)"
  muted: "oklch(0.70 0.012 110)"
  primary: "oklch(0.72 0.11 110)"
  success: "oklch(0.72 0.13 150)"
  danger: "oklch(0.68 0.18 28)"
typography:
  title:
    fontFamily: "Segoe UI Variable, Aptos, system-ui, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 650
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Segoe UI Variable, Aptos, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Cascadia Code, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  sm: "4px"
  md: "8px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  status-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "{spacing.lg}"
---

# Design System: DevFlow Assistant

## 1. Overview

**Creative North Star: "The Legible Control Room"**

DevFlow is a dark-first working surface built for extended, attentive use. Its
discipline comes from Linear, its calm from Vercel, and its transparent evidence
trail from GitHub. Information is dense when the work demands it, but grouping,
alignment, and restrained contrast prevent the pipeline from becoming noisy.

The interface rejects marketing-page theatrics, decorative AI motifs, and
card-heavy dashboards. State—not decoration—earns color.

**Key Characteristics:**

- Compact, crisp hierarchy
- Dark neutral architecture
- Monospace identifiers and metadata
- Familiar developer-tool affordances
- Color reserved for risk and workflow state

## 2. Colors

Near-neutral dark layers make long sessions comfortable; a quiet olive primary
anchors identity without competing with semantic state colors.

### Primary

- **Control Olive** (`oklch(0.72 0.11 110)`): focus and active-system accents.

### Secondary

- **Verified Green** (`oklch(0.72 0.13 150)`): successful checks and ready state.
- **Gate Red** (`oklch(0.68 0.18 28)`): failure and approval-blocking state.

### Neutral

- **Black Canvas** (`oklch(0.105 0 0)`): application background.
- **Olive Charcoal** (`oklch(0.145 0.008 110)`): primary working surface.
- **Raised Charcoal** (`oklch(0.185 0.01 110)`): active or nested surface.
- **Quiet Line** (`oklch(0.30 0.012 110)`): structure and dividers.
- **Primary Ink** (`oklch(0.94 0.006 110)`): high-contrast text.
- **Muted Ink** (`oklch(0.70 0.012 110)`): supporting text.

**The Evidence Color Rule.** Color must communicate system identity, state,
risk, or action. If it does none of those jobs, remove it.

## 3. Typography

**Display Font:** Segoe UI Variable (with Aptos and system-ui fallbacks)  
**Body Font:** Segoe UI Variable (with Aptos and system-ui fallbacks)  
**Label/Mono Font:** Cascadia Code (with Consolas and monospace fallbacks)

**Character:** A restrained product sans keeps controls familiar; monospace
makes IDs, stages, paths, and timing data immediately distinguishable.

### Hierarchy

- **Title** (650, 2.5rem, 1.05): page-level identity and major views.
- **Body** (400, 1rem, 1.6): descriptions capped near 70 characters.
- **Label** (600, 0.75rem, 1.4): technical metadata and compact state labels.

**The Working-Type Rule.** Decorative display typography never enters the app
shell; hierarchy comes from weight, size, and placement.

## 4. Elevation

The system is flat by default. Tonal layering and one-pixel dividers establish
depth; shadows are reserved for temporary overlays in later phases.

**The Flat State Rule.** Persistent surfaces never float decoratively.

## 5. Components

### Cards / Containers

- **Corner Style:** restrained (`8px`)
- **Background:** Olive Charcoal
- **Shadow Strategy:** none
- **Border:** one-pixel Quiet Line
- **Internal Padding:** `24px`

### Status

- **Style:** a shape, short label, and explanatory text always accompany color.
- **State:** loading may pulse gently; ready and error states remain static.

### Navigation

Future navigation uses the product sans, a clear current-location treatment,
visible keyboard focus, and conventional app-shell placement.

## 6. Do's and Don'ts

### Do:

- **Do** use color only for identity, action, and semantic state.
- **Do** keep primary text at AA contrast or better on every surface.
- **Do** pair color state with text and shape.
- **Do** preserve familiar diff, review, history, and approval conventions.
- **Do** expose visible `:focus-visible` treatment on every control.

### Don't:

- **Don't** build a marketing surface, playful AI companion, neon cyberpunk
  console, or generic card-heavy SaaS dashboard.
- **Don't** use decorative gradients, ornamental motion, oversized hero
  typography, or excessive rounding.
- **Don't** use colored side-stripe borders, nested cards, or glassmorphism.
- **Don't** use color when it does not communicate state.
