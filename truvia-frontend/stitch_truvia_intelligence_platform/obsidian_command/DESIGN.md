---
name: Obsidian Command
colors:
  surface: '#131318'
  surface-dim: '#131318'
  surface-bright: '#39383e'
  surface-container-lowest: '#0e0e13'
  surface-container-low: '#1b1b20'
  surface-container: '#1f1f25'
  surface-container-high: '#2a292f'
  surface-container-highest: '#35343a'
  on-surface: '#e4e1e9'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#e4e1e9'
  inverse-on-surface: '#303036'
  outline: '#908fa0'
  outline-variant: '#464555'
  surface-tint: '#c1c1ff'
  primary: '#c1c1ff'
  on-primary: '#1200a9'
  primary-container: '#5d5fef'
  on-primary-container: '#faf7ff'
  inverse-primary: '#4849da'
  secondary: '#c1c1ff'
  on-secondary: '#26276f'
  secondary-container: '#3d3e87'
  on-secondary-container: '#adaefe'
  tertiary: '#edc221'
  on-tertiary: '#3c2f00'
  tertiary-container: '#cea700'
  on-tertiary-container: '#4e3e00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c1c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2e2bc2'
  secondary-fixed: '#e1dfff'
  secondary-fixed-dim: '#c1c1ff'
  on-secondary-fixed: '#0f0d5a'
  on-secondary-fixed-variant: '#3d3e87'
  tertiary-fixed: '#ffe083'
  tertiary-fixed-dim: '#edc221'
  on-tertiary-fixed: '#231b00'
  on-tertiary-fixed-variant: '#564500'
  background: '#131318'
  on-background: '#e4e1e9'
  surface-variant: '#35343a'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-lg:
    fontFamily: Manrope
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-page: 40px
  card-padding: 20px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is engineered for **Truvia Intelligence**, catering to high-stakes decision-makers in security and data analysis. The brand personality is authoritative, precise, and visionary. It evokes the feeling of a futuristic Command & Control center—calm under pressure, yet pulsing with live data.

The visual style is a sophisticated blend of **Modern Minimalism** and **Glassmorphism**. It utilizes deep, obsidian-like layering to create an infinite sense of depth, allowing mission-critical data points to "glow" against a void-like backdrop. The aesthetic is grounded by rigorous alignment and structural integrity, ensuring that while the UI feels cutting-edge, it remains functional for long-duration monitoring.

## Colors

The palette is anchored in an "Obsidian" base (#0A0A0F) to minimize eye strain and maximize the "pop" of data visualizations. 

- **Primary & Secondary Blues:** These evolved navy tones maintain Truvia’s professional heritage while gaining a luminous, digital quality.
- **Data Accents:** Purple and Gold are reserved for high-priority insights, creating a clear visual hierarchy between "System" (blue/neutral) and "Insight" (purple/gold).
- **Glassmorphism:** Secondary overlays utilize semi-transparent surfaces with a 1px border at low opacity (10-15%) to simulate layered glass without cluttering the interface.

## Typography

The typography strategy prioritizes rapid scanning of quantitative data. **Manrope** is used for all primary UI text to provide a modern, balanced feel that remains legible at small sizes. 

For technical data points, labels, and system status codes, **JetBrains Mono** is introduced. This monospaced font reinforces the "Intelligence" brand, lending a precise, developer-adjacent aesthetic to mathematical outputs and terminal-style logs. Data-heavy displays should use `data-lg` for primary metrics to ensure they dominate the visual field.

## Layout & Spacing

This design system utilizes a **12-column fluid grid** for the main workspace, allowing dashboard widgets to span flexible widths (typically 3, 4, 6, or 12 columns).

- **Margins & Gutters:** High-density information is managed through generous 24px gutters, preventing data clusters from bleeding into one another. 
- **Vertical Rhythm:** Elements are spaced using a 4px base unit. 
- **Adaptive Reflow:** On Tablet, the 12-column grid collapses to 8, with cards typically stacking into 2 columns. On Mobile, it transitions to a 4-column grid with full-width cards and reduced page margins (16px).

## Elevation & Depth

Hierarchy is established through **Tonal Layering** and **Luminous Outlines** rather than traditional heavy shadows.

1.  **Level 0 (Base):** The obsidian background (#0A0A0F).
2.  **Level 1 (Cards):** Surface-charcoal (#12121A) with a subtle 1px inner stroke of white at 5% opacity. This creates a "razor-thin" edge definition.
3.  **Level 2 (Overlays/Modals):** Glassmorphism surfaces. These use a background blur (20px-40px) and a semi-transparent fill.
4.  **Glow Effects:** Critical data points and active chart lines use an outer glow (drop-shadow) with 0px offset and a blur of 10-15px using the accent color (e.g., purple or blue) at 30% opacity.

## Shapes

The shape language balances the "Futuristic" and "Grounded" aspects of the brand. A **Rounded (0.5rem)** base is applied to all standard cards and input fields. This softens the high-contrast color palette, making the interface feel approachable. 

Larger containers (e.g., main dashboard panels) should use `rounded-xl` (1.5rem) to create distinct "pods" of information. Interactive elements like tags or "Beta" chips should be pill-shaped to differentiate them from actionable buttons.

## Components

- **Buttons:** Primary buttons use a solid gradient (Primary Blue to Accent Purple) with white text. Secondary buttons are "Ghost" style with the 1px luminous border.
- **Data Cards:** High-contrast containers. They must include a "Header" section with a label-font title and an optional icon.
- **Glow Charts:** Line charts must use a 2px stroke width with a matching color glow. Area charts should use a vertical gradient from the accent color (20% opacity) to transparent.
- **Radial Gauges:** Used for "Intelligence Scores" or "Threat Levels," featuring a thick circular stroke and a centered `data-lg` numeric value.
- **Input Fields:** Dark fill (#0A0A0F) with a subtle bottom border that illuminates (changes color) when focused.
- **Chips/Status:** Small, high-contrast badges. Success status uses a low-opacity green background with a bright green dot indicator.