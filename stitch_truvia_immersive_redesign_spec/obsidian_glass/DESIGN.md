---
name: Obsidian Glass
colors:
  surface: '#121317'
  surface-dim: '#121317'
  surface-bright: '#38393d'
  surface-container-lowest: '#0d0e12'
  surface-container-low: '#1a1b1f'
  surface-container: '#1e1f23'
  surface-container-high: '#292a2e'
  surface-container-highest: '#343538'
  on-surface: '#e3e2e7'
  on-surface-variant: '#c3c5d7'
  inverse-surface: '#e3e2e7'
  inverse-on-surface: '#2f3034'
  outline: '#8d90a0'
  outline-variant: '#434654'
  surface-tint: '#b5c4ff'
  primary: '#b5c4ff'
  on-primary: '#00287c'
  primary-container: '#658aff'
  on-primary-container: '#00226d'
  inverse-primary: '#1c53d7'
  secondary: '#e6feff'
  on-secondary: '#003739'
  secondary-container: '#00f4fe'
  on-secondary-container: '#006c71'
  tertiary: '#ffb787'
  on-tertiary: '#512400'
  tertiary-container: '#e07314'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b5c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#003bae'
  secondary-fixed: '#63f7ff'
  secondary-fixed-dim: '#00dce5'
  on-secondary-fixed: '#002021'
  on-secondary-fixed-variant: '#004f53'
  tertiary-fixed: '#ffdcc7'
  tertiary-fixed-dim: '#ffb787'
  on-tertiary-fixed: '#311300'
  on-tertiary-fixed-variant: '#723600'
  background: '#121317'
  on-background: '#e3e2e7'
  surface-variant: '#343538'
typography:
  display-xl:
    fontFamily: Outfit
    fontSize: 64px
    fontWeight: '700'
    lineHeight: 72px
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.1em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  container-max: 1440px
---

## Brand & Style

The design system is engineered for high-stakes public safety and fraud detection, where clarity meets technical sophistication. It employs a **Dark Glassmorphism** aesthetic, utilizing layered translucency and light-refractive properties to organize complex data streams.

The personality is **vigilant, cinematic, and authoritative**. By combining deep space-black backgrounds with vibrant, glowing accents, the UI directs focus toward critical anomalies while maintaining a sense of spatial depth. Visual hierarchy is established through "light-leaks" and soft neon glows that act as silent alerts, creating a high-density environment that feels responsive and alive.

## Colors

This design system utilizes a high-contrast, dark-first palette to maximize legibility in low-light operations centers.

- **The Canvas:** A monolithic near-black (#06070a) serves as the infinite void for data visualization.
- **Electric Accents:** The primary Blue (#4f7bff) is used for active states and interactive elements, often paired with a secondary cyan for data gradients.
- **Semantic Logic:** 
  - **Crimson:** Reserved for immediate fraud threats and critical system failures.
  - **Amber:** Denotes high-risk behavior or pending investigations.
  - **Mint:** Signals resolved cases or healthy system throughput.
- **Glass Surfaces:** Containers use a semi-transparent white (4-7% opacity) to catch background light, paired with 1px "hairline" borders to define volume without adding visual weight.

## Typography

The typography strategy balances high-impact data visualization with technical readability.

- **Display & Headers:** 'Outfit' provides a geometric, modern tech feel. It should always be set with tight tracking (letter-spacing) to emphasize its structural, interlocking nature.
- **Functional Text:** 'Inter' is used for all data-rich areas, logs, and body content. It is configured with generous line-heights to ensure that even in high-density dashboards, the information remains scannable and accessible.
- **Data Labels:** Use 'Inter' in Bold or Semi-Bold at small sizes with expanded letter spacing for all metadata and axis labels to create a "digital HUD" aesthetic.

## Layout & Spacing

The layout uses a **Fluid Spatial Grid** designed for multi-monitor surveillance setups and mobile field reports.

- **Grid Model:** A 12-column system on desktop that collapses to 4 columns on mobile. 
- **Spacing Rhythm:** Based on an 8px base unit. Component internal padding should favor larger horizontal breathing room (e.g., 24px) versus vertical (e.g., 16px) to maintain a sleek, wide-screen look.
- **Adaptive Reflow:** Cards in the dashboard use CSS Grid auto-fit to reorganize based on screen width, ensuring that data visualizations never lose their aspect ratio integrity.

## Elevation & Depth

This design system relies on physical light metaphors rather than traditional drop shadows.

- **Stacking Logic:** Background (#06070a) > Mid-ground (Glass containers with 20px Backdrop Blur) > Foreground (Interactive elements with glow states).
- **Glass Effects:** Surfaces are rendered with a 1px solid border at 10% opacity on the top and left, and 5% on the bottom and right, simulating a light source from the top-left.
- **The Glow:** Elevation is signaled by "Bloom." Active cards or high-priority alerts should project a soft, diffused outer glow (e.g., 30px blur, 15% opacity) in their respective semantic color (Blue/Crimson/Amber).

## Shapes

The shape language is defined by oversized radii that soften the technical nature of the data. 

All primary dashboard cards and glass containers must use a **24px (rounded-xl)** corner radius. Smaller utility components like input fields and buttons follow a **12px (rounded-md)** standard. The contrast between large container curves and slightly sharper internal elements creates a "nested shell" appearance.

## Components

### Buttons & Interaction
- **Primary:** Gradient-filled (#4f7bff to #00f5ff) with a subtle inner-white stroke. On hover, the "bloom" intensity increases.
- **Ghost:** Transparent with a 1px white-glass border. Text is Inter Medium.

### Input Fields
- Dark, recessed backgrounds (2% opacity) with a 1px bottom border that glows Blue on focus.

### Data Chips
- Small, pill-shaped indicators with high-saturation backgrounds and white text. For fraud alerts, these should pulsate slightly using a CSS keyframe opacity animation.

### Dashboard Cards
- The core of the system. Every card features a `backdrop-filter: blur(20px)`, a hairline border, and a 24px radius. Use count-up animations for primary numeric metrics to provide a sense of real-time activity.

### Status Gauges
- Circular or semi-circular "ring" charts. Use a thick stroke for the progress and a dimmed, 5% opacity version of the same color for the "track."