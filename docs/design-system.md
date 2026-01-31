# Sentinel Dashboard Design System

A comprehensive design system document for replicating the Sentinel Dashboard UI.

---

## 1. Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| Framework | Next.js | 16 (App Router) |
| UI Library | React | 19 |
| Component Library | shadcn/ui | new-york style |
| Primitives | Radix UI | Latest |
| Styling | Tailwind CSS | 4 |
| Icons | Lucide React | 0.555.0 |
| Fonts | Inter, JetBrains Mono | Google Fonts |
| Charts | Recharts | 3.5.1 |
| Forms | React Hook Form + Zod | 7.68.0 / 4.1.13 |
| Utilities | clsx, tailwind-merge, CVA | Latest |

---

## 2. Color System

### Design Tokens (CSS Variables)

All colors use CSS custom properties with both HSL fallbacks and modern OKLch values.

#### Light Mode (Default)

```css
:root {
  /* Core Colors */
  --background: oklch(1 0 0);                    /* Pure white */
  --foreground: oklch(0.129 0.042 264.695);     /* Dark navy */

  /* Primary (Dark blue) */
  --primary: oklch(0.208 0.042 265.755);
  --primary-foreground: oklch(0.984 0.003 247.858);

  /* Secondary (Light gray) */
  --secondary: oklch(0.968 0.007 247.896);
  --secondary-foreground: oklch(0.208 0.042 265.755);

  /* Muted */
  --muted: oklch(0.968 0.007 247.896);
  --muted-foreground: oklch(0.554 0.046 257.417);

  /* Accent */
  --accent: oklch(0.968 0.007 247.896);
  --accent-foreground: oklch(0.208 0.042 265.755);

  /* Destructive (Red) */
  --destructive: oklch(0.577 0.245 27.325);
  --destructive-foreground: oklch(0.984 0.003 247.858);

  /* Borders & Inputs */
  --border: oklch(0.929 0.013 255.508);
  --input: oklch(0.929 0.013 255.508);
  --ring: oklch(0.704 0.04 256.788);

  /* Radius */
  --radius: 0.625rem;
}
```

#### Dark Mode

```css
.dark {
  --background: oklch(0.129 0.042 264.695);
  --foreground: oklch(0.984 0.003 247.858);
  --primary: oklch(0.929 0.013 255.508);
  --primary-foreground: oklch(0.208 0.042 265.755);
  --secondary: oklch(0.279 0.041 260.031);
  --secondary-foreground: oklch(0.984 0.003 247.858);
  --muted: oklch(0.279 0.041 260.031);
  --muted-foreground: oklch(0.704 0.04 256.788);
  --accent: oklch(0.279 0.041 260.031);
  --accent-foreground: oklch(0.984 0.003 247.858);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.551 0.027 264.364);
}
```

### Semantic Color Usage

| Purpose | Light Mode | Tailwind Class |
|---------|------------|----------------|
| Page background | Light gray | `bg-gray-50` |
| Card background | White | `bg-white` |
| Primary text | Dark navy | `text-gray-900` |
| Secondary text | Medium gray | `text-gray-600` |
| Tertiary text | Light gray | `text-gray-500` |
| Borders | Light gray | `border-gray-200` |
| Success/Approve | Green | `text-green-600`, `bg-green-50` |
| Warning/Review | Amber | `text-amber-600`, `bg-amber-50` |
| Error/Reject | Red | `text-red-600`, `bg-red-50` |

### Risk Level Colors

| Risk Level | Hex Code | Usage |
|------------|----------|-------|
| Low | `#22c55e` (green-500) | Safe transactions |
| Medium | `#F59E0B` (amber-500) | Review required |
| High | `#EF4444` (red-500) | High risk |
| Critical | `#EF4444` with pulse | Immediate attention |

### Chart Colors (OKLch)

```css
--chart-1: oklch(0.646 0.222 41.116);   /* Orange */
--chart-2: oklch(0.6 0.118 184.704);    /* Cyan */
--chart-3: oklch(0.398 0.07 227.392);   /* Purple */
--chart-4: oklch(0.828 0.189 84.429);   /* Yellow-green */
--chart-5: oklch(0.769 0.188 70.08);    /* Orange-yellow */
```

---

## 3. Typography

### Font Families

```css
font-sans: ["var(--font-inter)", "system-ui", "sans-serif"]
font-mono: ["var(--font-mono)", "monospace"]
```

**Primary Font:** Inter (body text, UI elements)
**Monospace Font:** JetBrains Mono (code, technical data)

### Font Loading (Next.js)

```typescript
import { Inter, JetBrains_Mono } from "next/font/google";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});
```

### Type Scale

| Element | Class | Size |
|---------|-------|------|
| Page heading | `text-xl sm:text-2xl font-semibold` | 20px → 24px |
| Card title | `text-lg sm:text-xl font-semibold` | 18px → 20px |
| Section label | `text-sm font-medium uppercase tracking-wide` | 14px |
| Body text | `text-sm` | 14px |
| Small text | `text-xs` | 12px |
| Large display | `text-6xl font-bold` | 60px (risk score) |

### Text Colors

- Primary: `text-gray-900`
- Secondary: `text-gray-600`
- Muted: `text-gray-500` or `text-muted-foreground`
- Placeholder: `text-gray-400`

---

## 4. Spacing System

### Base Unit
Uses Tailwind's default 4px base unit.

### Common Patterns

| Context | Mobile | Desktop | Classes |
|---------|--------|---------|---------|
| Page padding | 16px vertical, 16px horizontal | 32px, 24px | `py-6 px-4 sm:py-8 sm:px-6 lg:px-8` |
| Card padding | 16px | 24px | `p-4 sm:p-6` |
| Section gaps | 24px | 32px | `space-y-6 sm:space-y-8` |
| Element gaps | 12px | 24px | `gap-3 sm:gap-6` |

### Container

```css
container: {
  center: true,
  padding: "2rem",
  screens: {
    "2xl": "1400px"
  }
}
```

Use: `max-w-7xl mx-auto` for page content.

---

## 5. Border Radius

```css
--radius: 0.625rem;  /* 10px base */
--radius-sm: calc(var(--radius) - 4px);  /* 6px */
--radius-md: calc(var(--radius) - 2px);  /* 8px */
--radius-lg: var(--radius);               /* 10px */
--radius-xl: calc(var(--radius) + 4px);  /* 14px */
```

### Usage

| Element | Class |
|---------|-------|
| Cards | `rounded-sm` (6px) |
| Buttons | `rounded-sm` |
| Inputs | `rounded-sm` |
| Badges | `rounded-sm` |
| Full round | `rounded-full` |

---

## 6. Shadows

The design uses minimal shadows, preferring borders for separation.

| Element | Style |
|---------|-------|
| Cards | No shadow, `border border-gray-200` |
| Dialogs | `shadow-lg` |
| Popovers | `shadow-md` |
| Active tabs | `shadow-sm` |

---

## 7. Components

### Button

**Variants:**
- `default`: `bg-primary text-primary-foreground hover:bg-primary/90`
- `destructive`: `bg-destructive text-white hover:bg-destructive/90`
- `outline`: `border border-input bg-background hover:bg-accent`
- `secondary`: `bg-secondary text-secondary-foreground hover:bg-secondary/80`
- `ghost`: `hover:bg-accent hover:text-accent-foreground`
- `link`: `text-primary underline-offset-4 hover:underline`

**Sizes:**
- `default`: `h-10 px-4 py-2`
- `sm`: `h-9 px-3`
- `lg`: `h-11 px-8`
- `icon`: `h-10 w-10`

**Primary action style:** `bg-gray-900 hover:bg-gray-800 text-white`

### Card

```
Card (rounded-sm border bg-white border-gray-200)
├── CardHeader (p-6, space-y-1.5)
│   ├── CardTitle (text-2xl font-semibold)
│   └── CardDescription (text-sm text-muted-foreground)
├── CardContent (p-6 pt-0)
└── CardFooter (flex items-center p-6 pt-0)
```

### Badge

**Variants:**
- `default`: `bg-primary text-primary-foreground`
- `secondary`: `bg-secondary text-secondary-foreground`
- `destructive`: `bg-destructive text-white`
- `outline`: `border text-foreground`

**Base:** `inline-flex items-center rounded-sm px-2.5 py-0.5 text-xs font-semibold`

### Input

```css
h-10 w-full rounded-sm border border-input bg-transparent px-3 py-1 text-sm
placeholder:text-muted-foreground
focus-visible:ring-1 focus-visible:ring-ring
disabled:cursor-not-allowed disabled:opacity-50
```

### Select

- Trigger: `h-10 w-full border border-input bg-transparent px-3 py-2`
- Content: `rounded-sm border bg-popover shadow-md`
- Item: `py-1.5 pl-2 pr-8 rounded-sm focus:bg-accent`

### Tabs

- List: `inline-flex h-auto items-center justify-center rounded-sm bg-gray-100 p-1 w-full`
- Trigger: `px-4 py-2 data-[state=active]:bg-white data-[state=active]:shadow-sm`
- Active: `text-gray-900 bg-white shadow-sm`

### Table

- Header: `border-b bg-transparent`
- Head cell: `h-12 px-4 text-muted-foreground font-medium`
- Body row: `border-b transition-colors hover:bg-muted/50`
- Cell: `p-4`

### Dialog/Modal

- Overlay: `fixed inset-0 z-50 bg-black/80`
- Content: `fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 max-w-lg`
- Animation: `animate-in fade-in-0 zoom-in-95`

### Alert

**Variants:**
- `default`: `bg-background text-foreground`
- `destructive`: `border-destructive/50 text-destructive bg-red-50`

---

## 8. Icons

**Library:** Lucide React

**Common sizes:**
- Small: `h-4 w-4`
- Medium: `h-5 w-5`
- Large: `h-6 w-6`

**Usage pattern:**
```tsx
import { Activity, AlertTriangle, CheckCircle } from "lucide-react";

<Activity className="h-4 w-4 text-gray-500" />
```

**Common icons used:**
- Navigation: `LayoutDashboard`, `FileStack`, `BarChart3`
- Status: `CheckCircle`, `AlertTriangle`, `XCircle`, `Clock`
- Actions: `Copy`, `Download`, `Trash2`, `ChevronDown`
- Content: `Globe`, `Building2`, `CreditCard`, `User`
- Feedback: `Loader2` (with `animate-spin`), `Zap`

---

## 9. Layout Patterns

### App Shell

```
AppShell (min-h-screen flex flex-col bg-gray-50)
├── DevbrewBanner (optional promotional bar)
├── NavHeader (sticky top-0 z-50)
├── main (flex-1)
│   └── Page content
└── Footer
```

### Page Container

```tsx
<div className="py-6 px-4 sm:py-8 sm:px-6 lg:px-8">
  <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
    {/* Page content */}
  </div>
</div>
```

### Navigation Header

- Sticky: `sticky top-0 z-50`
- Background: `bg-white border-b border-gray-200`
- Content: Logo (left), Nav items (center), Status (right)
- Active nav: `bg-gray-50 text-gray-900`

### Grid Layouts

**Dashboard (2+3 split):**
```tsx
<div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
  <div className="lg:col-span-2">{/* Left column */}</div>
  <div className="lg:col-span-3">{/* Right column */}</div>
</div>
```

**Stats cards:**
```tsx
<div className="grid grid-cols-3 sm:grid-cols-4 gap-3 sm:gap-6">
```

**Two-column form fields:**
```tsx
<div className="grid grid-cols-2 gap-4">
```

---

## 10. Responsive Breakpoints

| Breakpoint | Min Width | Usage |
|------------|-----------|-------|
| Default | 0px | Mobile-first base styles |
| `sm:` | 640px | Small tablets |
| `md:` | 768px | Tablets, show desktop nav |
| `lg:` | 1024px | Desktop layouts |
| `xl:` | 1280px | Large desktop |
| `2xl:` | 1400px | Max container width |

### Common Responsive Patterns

```css
/* Typography */
text-xl sm:text-2xl

/* Padding */
p-4 sm:p-6

/* Grid */
grid-cols-1 md:grid-cols-2 lg:grid-cols-4

/* Visibility */
hidden md:flex

/* Spacing */
gap-3 sm:gap-6
space-y-6 sm:space-y-8
```

---

## 11. Animations

### Built-in Animations

```css
/* Accordion */
animation: {
  "accordion-down": "accordion-down 0.2s ease-out",
  "accordion-up": "accordion-up 0.2s ease-out"
}

/* Dialog/Popover */
animate-in fade-in-0 zoom-in-95
animate-out fade-out-0 zoom-out-95
slide-in-from-top-2
```

### Custom Animations

**Loading spinner:**
```tsx
<Loader2 className="h-4 w-4 animate-spin" />
```

**Skeleton loading:**
```tsx
<div className="animate-pulse rounded-md bg-gray-200 h-4 w-full" />
```

**Status ping:**
```tsx
<span className="absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75 animate-ping" />
```

**Risk score pulse (critical):**
```tsx
<span className="animate-pulse text-red-600">87%</span>
```

**Transitions:**
```css
transition-colors
transition-all duration-500
transition-opacity
```

### Gauge Animation (Risk Score)

Custom easing function for score changes:
```typescript
const easeOutQuart = (t: number) => 1 - Math.pow(1 - t, 4);
// Duration: 800ms
```

---

## 12. Form Patterns

### Form Structure

```tsx
<Form>
  <FormField
    control={form.control}
    name="fieldName"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Label</FormLabel>
        <FormControl>
          <Input placeholder="Placeholder..." {...field} />
        </FormControl>
        <FormDescription>Helper text</FormDescription>
        <FormMessage /> {/* Error message */}
      </FormItem>
    )}
  />
</Form>
```

### Label Styling

```css
text-sm font-medium text-gray-700
```

### Error States

- Label: `text-destructive`
- Input: `border-destructive`
- Message: `text-sm font-medium text-destructive`

### Button Row

```tsx
<div className="flex gap-3">
  <Button type="submit" className="flex-1 bg-gray-900 hover:bg-gray-800">
    Submit
  </Button>
  <Button type="button" variant="outline">
    Clear
  </Button>
</div>
```

---

## 13. Data Display Components

### Risk Gauge

Semi-circular gauge using Recharts PieChart:
- Size: `h-64`
- Colors: Green (low) → Amber (medium) → Red (high/critical)
- Center: Large percentage (`text-6xl font-bold`)
- Risk level label below
- Glow effect for high risk: `blur-3xl opacity-50`

### Feature Importance (SHAP)

- Card with divided list (`divide-y`)
- Bidirectional bars from center
- Green bars: reduces risk (negative SHAP)
- Red bars: increases risk (positive SHAP)
- Icons: `TrendingUp` (red), `TrendingDown` (green)

### Sanctions Card

- Border color based on match: `border-red-200` (match) vs `border-gray-200`
- Match rank badges: `bg-amber-100` (#1), `bg-gray-100` (#2+)
- Score bars: color-coded percentage width
- Expandable details section

### Transaction History

- Scrollable: `max-h-[320px] overflow-y-auto`
- Risk dot indicators (colored circles)
- Selected state: `bg-gray-100`
- Hover: `hover:bg-gray-50`

### Velocity Indicators

Inline badges showing transaction counts:
- Normal (green): `bg-green-100 text-green-700`
- Elevated (amber): `bg-amber-100 text-amber-700`
- High (red): `bg-red-100 text-red-700`

---

## 14. Decision Display Patterns

| Decision | Text Color | Badge |
|----------|------------|-------|
| Approve | `text-green-600` | `bg-green-100 text-green-800` |
| Review | `text-amber-600` | `bg-amber-100 text-amber-800` |
| Reject | `text-red-600` | `bg-red-100 text-red-800` |

### Latency Badge

Color-coded by performance:
- ≤100ms: `bg-green-100 text-green-800`
- 100-200ms: `bg-yellow-100 text-yellow-800`
- >200ms: `bg-red-100 text-red-800`

---

## 15. Chart Styling (Recharts)

### Common Configuration

```tsx
<ResponsiveContainer width="100%" height={250}>
  <BarChart data={data}>
    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
    <XAxis
      dataKey="name"
      tick={{ fill: '#64748b', fontSize: 12 }}
      axisLine={{ stroke: '#e2e8f0' }}
    />
    <YAxis
      tick={{ fill: '#64748b', fontSize: 12 }}
      axisLine={{ stroke: '#e2e8f0' }}
    />
    <Tooltip
      contentStyle={{
        backgroundColor: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: '6px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}
    />
  </BarChart>
</ResponsiveContainer>
```

### Chart Heights

- Default: `h-[200px] sm:h-[250px]`
- Large: `h-[300px]`

---

## 16. Utility Functions

### Class Name Merging

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Usage:
```tsx
<div className={cn("base-classes", conditional && "conditional-class", className)} />
```

---

## 17. File Structure

```
apps/web/src/
├── app/
│   ├── layout.tsx          # Root layout with fonts
│   ├── page.tsx            # Dashboard
│   ├── analytics/page.tsx  # Analytics
│   ├── batch/page.tsx      # Batch processing
│   └── globals.css         # Global styles & CSS variables
├── components/
│   ├── ui/                 # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── badge.tsx
│   │   ├── select.tsx
│   │   ├── tabs.tsx
│   │   ├── table.tsx
│   │   ├── dialog.tsx
│   │   ├── alert.tsx
│   │   ├── form.tsx
│   │   ├── progress.tsx
│   │   ├── skeleton.tsx
│   │   └── ...
│   ├── app-shell.tsx       # Main layout wrapper
│   ├── nav-header.tsx      # Navigation
│   ├── footer.tsx          # Footer
│   ├── transaction-form.tsx
│   ├── risk-gauge.tsx
│   ├── feature-importance.tsx
│   ├── sanctions-card.tsx
│   ├── velocity-indicators.tsx
│   └── ...
└── lib/
    └── utils.ts            # cn() helper
```

---

## 18. Configuration Files

### tailwind.config.ts

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" }
    },
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

### components.json (shadcn/ui)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

---

## 19. Design Principles

1. **Minimalist**: Clean interfaces with purposeful whitespace
2. **Functional**: Design serves the data, not decoration
3. **Accessible**: Clear contrast, semantic HTML, ARIA labels
4. **Consistent**: Reusable components with predictable behavior
5. **Responsive**: Mobile-first with graceful scaling
6. **Performance-focused**: Light animations, efficient rendering
7. **Intent-based colors**: Green = safe, Amber = caution, Red = danger

---

## 20. Quick Reference

### Most Used Classes

```css
/* Containers */
max-w-7xl mx-auto
py-6 px-4 sm:py-8 sm:px-6 lg:px-8
space-y-6 sm:space-y-8

/* Cards */
rounded-sm border bg-white border-gray-200
p-4 sm:p-6

/* Text */
text-gray-900 (primary)
text-gray-600 (secondary)
text-gray-500 (muted)
text-sm font-medium (labels)

/* Buttons */
bg-gray-900 hover:bg-gray-800 text-white
border border-gray-200 hover:bg-gray-50

/* Status Colors */
text-green-600 bg-green-50 (success)
text-amber-600 bg-amber-50 (warning)
text-red-600 bg-red-50 (error)

/* Responsive */
hidden md:flex
grid-cols-1 lg:grid-cols-2
text-sm sm:text-base
```

This design system document provides all the information needed to replicate the Sentinel Dashboard UI in another project.
