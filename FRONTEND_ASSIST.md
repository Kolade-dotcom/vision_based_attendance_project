---
name: frontend-assist
description: >
  Anti-vibecode frontend guardrails. Use this skill ANY time you are generating, reviewing,
  or editing frontend code — HTML, CSS, JS, React, Vue, Svelte, or any UI framework.
  Trigger on: "build me a page", "create a component", "make a dashboard", "landing page",
  "UI", "website", "web app", "frontend", "layout", "design", or any request that will
  produce visible interface code. This skill exists to eliminate the generic, soulless,
  instantly-recognizable aesthetic of AI-generated UI (commonly called "vibecoded" UI).
  It is a checklist and philosophy document. Read it BEFORE writing any frontend code.
---

# FRONTEND_ASSIST — The Anti-Vibecode Manifesto

> A vibecoded UI is not one that was built with AI.
> A vibecoded UI is one that *looks* like it was built with AI.
> The goal is not to avoid AI — it is to avoid the default.

This document is a field guide. It catalogs every telltale pattern that makes a UI scream
"an LLM built this" and provides concrete, enforceable rules to avoid each one.
Read the relevant sections before generating any frontend code.

---

## Part 1 — The Telltales (Know Your Enemy)

These are the dead giveaways. Each pattern below is something AI-generated UIs do
*by default* because the training data is saturated with it. A single telltale is forgivable.
Three or more in the same interface and you have unmistakable vibecode.

### 1.1 — The Indigo-Purple Gradient Plague

**What it looks like:** Buttons are `bg-indigo-500` or `bg-violet-600`. Hero sections have a
purple-to-blue gradient. Cards fade into lavender. The entire page is drowning in the
blue-violet spectrum.

**Why it happens:** Tailwind CSS's default examples used `indigo-500` extensively for years.
This color saturated public codebases, which became LLM training data. The model learned
that indigo = "modern web design." Adam Wathan (Tailwind's creator) publicly acknowledged
this feedback loop.

**The rule:** NEVER use indigo, violet, or purple as the primary brand color unless the user
explicitly requests it. If no color preference is given, choose from the full spectrum —
warm earth tones, deep teals, burnt oranges, olive greens, slate blues, warm grays. The
color should feel *chosen*, not *defaulted to*.

---

### 1.2 — The Shadcn/Radix Uncanny Valley

**What it looks like:** Every component looks like it was pulled from the shadcn/ui docs
page. Rounded-lg borders everywhere. The same muted foreground/background token pairings.
Cards with identical padding, identical shadows, identical border-radius. Buttons that
all look like the shadcn default button variants. The whole page has the aesthetic of a
component library demo, not a product.

**Why it happens:** shadcn/ui is the single most referenced component library in modern AI
training data. LLMs default to its patterns the way humans default to breathing.

**The rule:** Component libraries are tools, not aesthetics. If using shadcn (or any library),
you MUST customize:
- Border radius (don't use the default `rounded-lg` everywhere — mix sharp and soft)
- Shadow profiles (create a custom shadow scale, not the Tailwind defaults)
- Color tokens (override the default HSL values with project-specific ones)
- Spacing rhythm (don't use `p-4` and `p-6` on everything — develop a deliberate scale)

A well-themed shadcn project should be unrecognizable as shadcn.

---

### 1.3 — The "Three Feature Cards" Layout

**What it looks like:** A centered heading, a subtitle in muted gray, then exactly three
cards in a row — each with an icon, a title, and a short description. Sometimes four cards.
The spacing is perfectly even. The icons are from Lucide. The whole section could be
swapped between any two AI-generated landing pages and nobody would notice.

**Why it happens:** The "features section with N cards" is the single most common pattern
in landing page templates. Every tutorial, every Tailwind UI example, every SaaS template
uses this exact layout. The LLM has seen it ten million times.

**The rule:** NEVER default to the symmetric card grid for feature sections. Alternatives:
- Asymmetric layouts (one large card, two small)
- Bento grids with varying cell sizes
- A single-column list with generous whitespace
- A staggered/offset layout
- An interactive element (tabs, accordion, carousel) instead of a static grid
- Full-width alternating sections (image left / text right, then flip)

If cards ARE the right choice, vary them — different sizes, different orientations,
different levels of visual emphasis. The grid should have *hierarchy*, not *symmetry*.

---

### 1.4 — The "Hero-Features-Testimonials-CTA-Footer" Skeleton

**What it looks like:** The page follows this exact section order:
1. Hero with big heading + subheading + two buttons
2. "Trusted by" logo bar
3. Features (three cards)
4. Testimonials (three quotes)
5. Pricing table
6. Final CTA
7. Footer with four columns

Every section is full-width. Every section has identical top/bottom padding. The page
reads like a checklist, not a story.

**Why it happens:** This is the SaaS landing page template. It exists in thousands of
Tailwind templates, and LLMs have memorized it as "the shape of a landing page."

**The rule:** A page should have a *narrative arc*, not a template skeleton. Before laying
out sections, answer:
- What is the user's emotional state when they arrive?
- What is the single most important thing they should understand?
- What is the journey from curiosity to action?

Then design sections that serve that journey. Skip sections that don't earn their space.
Vary section heights, widths, and visual treatments. Break the full-width monotony with
constrained-width sections, edge-to-edge images, or overlapping elements.

---

### 1.5 — The Typography Flatline

**What it looks like:** Inter for everything. Or Roboto. Or system-ui. Body text at 16px,
headings are just bigger versions of the same font. No size contrast between heading levels.
No letterspacing adjustments. No font-weight variety beyond regular and bold. Line-height
is the browser default or `leading-relaxed` on everything.

**Why it happens:** LLMs default to "safe" fonts because they appear most in training data.
Inter is the most common choice because it's Google Fonts' default suggestion and
appears in countless starter templates.

**The rule:**
- NEVER use Inter, Roboto, or system-ui as the sole typeface unless explicitly requested.
- Every project needs a *type pairing*: a display/heading font and a body font. These
  should be from different families or at minimum different weights/styles.
- Headings should use noticeable letterspacing adjustments (usually tighter: `-0.02em`
  to `-0.05em` for large text).
- Establish a clear size scale with real contrast: if body is 16px, H1 should be 48px+,
  not 24px. Timid size scales produce flat, lifeless pages.
- Use variable fonts when possible for precise weight control.
- Consider serif fonts. AI almost never picks serifs, which makes them an instant
  differentiator.

Good font choices to explore (non-exhaustive): DM Sans, Sora, Outfit, Satoshi, Cabinet
Grotesk, General Sans, Instrument Serif, Fraunces, Clash Display, Plus Jakarta Sans,
Geist, Bricolage Grotesque. Rotate choices — never converge on the same font across
projects.

---

### 1.6 — The Emoji/Lucide Icon Carpet

**What it looks like:** Every list item has a ✅ or ✨ emoji. Every feature card has a
Lucide icon in a colored circle. Icons are used as decorative filler, not as functional
communication. The same icon style (outline, 24px, stroke-width 2) is used everywhere
with no variation.

**Why it happens:** LLMs reach for Lucide icons the way humans reach for their phone.
They're available, they're easy, and the model has seen them in every shadcn example.

**The rule:**
- Icons should *communicate*, not decorate. If removing the icon changes nothing about
  the user's understanding, remove the icon.
- When icons are needed, customize them: vary sizes, use filled variants, adjust stroke
  weight, or use a different icon set entirely (Phosphor, Tabler, Heroicons).
- NEVER put every icon in an identical colored circle. This is the #1 vibecoded icon
  pattern.
- Consider using typographic elements, numbers, or custom illustrations instead of
  generic icons.

---

### 1.7 — The "Works Great on Desktop, Broken on Mobile" Problem

**What it looks like:** The desktop layout is polished but the mobile version has:
- Overflowing text or containers
- Touch targets that are too small
- Sidebar that doesn't collapse
- Horizontal scroll on the page body
- Content that's simply squeezed, not redesigned

**Why it happens:** LLMs generate for the viewport they visualize (desktop). Mobile is an
afterthought — if addressed at all, it's with a blanket `md:` breakpoint that just stacks
columns.

**The rule:**
- Design mobile-first. Start with the mobile layout and *expand* to desktop, not the
  reverse.
- Every component needs explicit responsive behavior, not just column stacking.
- Touch targets must be minimum 44x44px (WCAG standard).
- Test at 375px, 768px, and 1280px — all three, every time.
- Navigation must have a mobile pattern (hamburger, bottom nav, drawer) — never leave
  a desktop nav bar on mobile.

---

### 1.8 — The State Vacuum

**What it looks like:** Beautiful static UI with no consideration for:
- Empty states ("no items yet")
- Loading states (no skeletons, no spinners, no progressive loading)
- Error states (no error messages, no retry buttons, no graceful degradation)
- Hover/focus/active states on interactive elements
- Disabled states
- Overflow behavior (what happens when text is longer than expected?)

The UI looks perfect with placeholder data but falls apart with real-world input.

**Why it happens:** LLMs optimize for the "golden path" — the scenario where everything
works perfectly. Edge cases require explicit prompting to address.

**The rule:**
- Every interactive component MUST have: default, hover, focus, active, disabled states.
- Every data-dependent view MUST have: loading, empty, error, and populated states.
- Every text container MUST handle overflow (truncation with ellipsis, line-clamp, or
  graceful wrapping).
- Forms MUST have validation states, error messages, and success feedback.
- Build the empty state first — it's the first thing real users will see.

---

### 1.9 — The Animation Uncanny Valley

**What it looks like:** Either zero animation (everything is static and lifeless) or
overdone animation where everything bounces, fades, slides, and scales on every
interaction. Common: `transition-all duration-300` slapped on everything. Scroll-triggered
fade-in animations on every single section (the "AOS library" effect).

**Why it happens:** LLMs either skip animation entirely or apply a uniform animation
pattern to everything. They don't understand the *hierarchy* of motion — that some
elements deserve emphasis and others should be still.

**The rule:**
- Motion should have *purpose*: guide attention, provide feedback, maintain spatial
  orientation, or create delight at key moments.
- Use motion sparingly. One well-orchestrated page entrance with staggered reveals
  creates more delight than animating every element.
- NEVER use `transition-all` — specify exactly which properties should transition.
- Hover states should be subtle (2-4px translate, slight scale, color shift). Not
  everything needs a hover effect.
- Page transitions should use staggered timing (50-100ms delays between elements)
  to create natural flow, not simultaneous pop-in.
- Prefer CSS transitions over JS animation libraries for simple interactions.

---

### 1.10 — The Copy Crimes

**What it looks like:** UI copy that screams "AI wrote this":
- Headlines like "Supercharge Your Workflow" or "Unlock the Power of X"
- Subheadings that are full paragraphs starting with "Whether you're a..."
- Button text like "Get Started Today" or "Start Your Journey"
- Placeholder testimonials with names like "Sarah M., Marketing Director"
- Feature descriptions full of buzzwords: "seamless," "intuitive," "cutting-edge,"
  "revolutionary," "game-changing"

**Why it happens:** LLMs generate marketing copy from the same pool of overused SaaS
clichés that dominate their training data.

**The rule:**
- Headlines should be specific, not generic. "Track every package in real time" beats
  "Supercharge Your Shipping."
- Button copy should describe the action: "Create account" not "Get Started Today."
- Avoid ALL of these words in UI copy: seamless, intuitive, cutting-edge, revolutionary,
  game-changing, supercharge, unlock, elevate, leverage, streamline, empower, harness.
- Placeholder content should feel real. Use specific names, specific roles, specific
  companies. Fake data should be plausible, not obviously generated.
- Error messages should be human: "We couldn't save your changes. Try again?" not
  "An unexpected error occurred."

---

### 1.11 — The Flat White Background Desert

**What it looks like:** White background. Content sections separated only by padding.
No texture, no depth, no atmosphere. Maybe a faint gray divider between sections.
The page feels like a Google Doc with nicer fonts.

**Why it happens:** White backgrounds are "safe." LLMs default to `bg-white` or
`bg-background` because it's the path of least visual risk.

**The rule:**
- Backgrounds should create *atmosphere*, not just hold content.
- Techniques: subtle gradients, noise/grain textures, dotted or grid patterns,
  alternating section backgrounds (light gray, off-white, accent-tinted), layered
  transparency, mesh gradients, or full-bleed images.
- Use `bg-neutral-50` or a warm off-white (`#FAFAF8`) instead of pure white (`#FFFFFF`).
  Pure white is harsh and clinical.
- Create depth with layered cards that use subtle shadows and slight background
  differences to establish a visual z-axis.

---

### 1.12 — The Accessibility Afterthought

**What it looks like:** No focus indicators (or focus indicators removed for aesthetics).
Low contrast text (light gray on white). Images without alt text. Interactive elements
that aren't keyboard navigable. Form inputs without labels. Color used as the only
indicator of state.

**Why it happens:** Accessibility requires deliberate effort and testing. LLMs generate
visually-oriented code and don't systematically verify WCAG compliance.

**The rule:**
- Color contrast MUST meet WCAG AA (4.5:1 for body text, 3:1 for large text).
- Every interactive element MUST have a visible focus state.
- Every image MUST have meaningful alt text (or `alt=""` if decorative).
- Every form input MUST have an associated `<label>`.
- Page structure MUST use semantic HTML (`<nav>`, `<main>`, `<section>`, `<article>`,
  `<header>`, `<footer>`) — not `<div>` soup.
- ARIA attributes should be present where semantic HTML is insufficient.

---

## Part 2 — The Antidotes (Build Like a Human)

### 2.1 — Start With a Design Decision, Not a Layout

Before writing any code, make three deliberate choices:

1. **Color identity**: Pick 1 primary color, 1 neutral scale, and 1 accent. Generate these
   from a reference (a photograph, a brand, a mood) — not from Tailwind defaults.

2. **Type pairing**: Choose a heading font and a body font. These set the entire personality
   of the page. A serif heading with a sans-serif body says "editorial." A geometric sans
   says "tech." A humanist sans says "friendly." Choose intentionally.

3. **Spatial personality**: Decide on your spacing philosophy. Generous whitespace with
   large type says "premium." Tight spacing with small type says "data-dense." Medium
   spacing with medium type says "generic" — avoid the middle.

### 2.2 — The "Screenshot Test"

After generating any UI, take a mental screenshot and ask:

- Could this be from any of the ten thousand AI-generated landing pages on the internet?
- If someone saw this screenshot with no context, would they assume it was AI-generated?
- Is there a single visual element that is *surprising* or *distinctive*?

If the answers are yes/yes/no, iterate. Change the color. Break the layout symmetry.
Add a distinctive typographic treatment. Give it a *point of view*.

### 2.3 — The Component Customization Checklist

For every component you generate, verify:

```
□ Border radius is NOT uniformly rounded-lg everywhere
□ Shadow is NOT the Tailwind default (shadow-md, shadow-lg)
□ Padding is NOT just p-4 or p-6 on everything
□ Colors are NOT from the Tailwind default palette without customization
□ The font is NOT Inter, Roboto, or system-ui (unless explicitly requested)
□ Hover/focus/active states are defined
□ The component handles overflow gracefully
□ The component is keyboard navigable
□ The component works at mobile widths
```

### 2.4 — The Spacing Rhythm Rule

Amateur UIs use the same spacing value everywhere. Professional UIs have rhythm.

- Establish a spacing scale: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128px.
- Use *larger* gaps between unrelated sections, *smaller* gaps between related elements.
- The gap between a heading and its body text should be *smaller* than the gap between
  two separate sections. This is called "proximity" and it's the single most important
  layout principle.
- Vertical rhythm should feel intentional. If every section has `py-16`, you have no
  rhythm — you have monotony.

### 2.5 — Color Theory for Non-Designers

If the user hasn't specified colors, don't reach for indigo. Instead:

- **Choose based on context**: Finance → deep blues, navy, forest green. Health → teal,
  warm greens, soft corals. Creative → bold primaries, unexpected combinations. Enterprise
  → restrained neutrals with one strong accent.
- **Build a full palette**: Primary (1 color, 3 shades), Neutral (8 shades from near-white
  to near-black), Accent (1 contrasting color for CTAs and highlights), Semantic (green
  for success, amber for warning, red for error).
- **Use opacity and tints**: Instead of picking 5 separate colors, use your primary at
  different opacities over light/dark backgrounds. This creates cohesion automatically.

### 2.6 — Layout Principles That Kill Vibecode

1. **Break the grid intentionally**: Use a consistent grid but let elements overflow it.
   An image that bleeds to the edge while text stays constrained creates visual interest.

2. **Vary section treatments**: Not every section should be full-width with centered
   content. Mix: constrained-width text, full-bleed images, asymmetric two-column layouts,
   overlapping elements.

3. **Create focal points**: Every page should have 1-2 elements that are *dramatically*
   different in scale from everything else. A huge number. An oversized heading. A
   full-screen image. This is what gives a page identity.

4. **Use real visual hierarchy**: If everything is medium-sized and medium-weight, nothing
   stands out. Crank up the contrast between primary and secondary content.

---

## Part 3 — Technical Hygiene (The Invisible Telltales)

These issues don't show up in screenshots but reveal AI-generated code to any developer
who inspects the source.

### 3.1 — HTML Structure

```
BAD (vibecoded):
<div class="container">
  <div class="header">
    <div class="nav">...</div>
  </div>
  <div class="main">
    <div class="section">...</div>
  </div>
  <div class="footer">...</div>
</div>

GOOD (semantic):
<header>
  <nav>...</nav>
</header>
<main>
  <section aria-labelledby="features-heading">...</section>
</main>
<footer>...</footer>
```

- Use semantic HTML elements, not div soup.
- Every landmark region should be present: header, nav, main, footer.
- Headings must follow hierarchy (h1 → h2 → h3, never skip levels).
- Lists should use `<ul>`/`<ol>`, not styled divs.

### 3.2 — CSS Organization

- Use CSS custom properties (variables) for ALL design tokens: colors, spacing, radii,
  shadows, font sizes. Never hard-code values that appear more than once.
- Group related properties logically (layout → sizing → spacing → visual → typography).
- Avoid `!important` except for genuine utility overrides.
- Avoid `transition: all` — always specify properties: `transition: transform 200ms ease,
  opacity 200ms ease`.
- Remove unused CSS. Vibecoded projects often have dead classes.

### 3.3 — Responsive Implementation

- Use `clamp()` for fluid typography: `font-size: clamp(1rem, 2.5vw, 1.5rem)`.
- Use container queries where supported, media queries as fallback.
- Test at actual device widths (375, 390, 414, 768, 1024, 1280, 1440), not just
  "mobile" and "desktop."
- Images must have `srcset` or responsive sizing — not fixed pixel widths.

### 3.4 — Performance

- Images must be lazy-loaded below the fold: `loading="lazy"`.
- Fonts must use `font-display: swap` to prevent invisible text.
- Critical CSS should be inlined or loaded first.
- Avoid loading entire icon libraries when using 5 icons.
- No layout shift: reserve space for images and dynamic content.

### 3.5 — Meta and SEO (Often Completely Missing)

Vibecoded sites almost universally forget:
- `<meta name="viewport" content="width=device-width, initial-scale=1">`
- `<meta name="description" content="...">`
- OpenGraph tags (`og:title`, `og:description`, `og:image`)
- Favicon (not the default or a placeholder)
- Proper `<title>` tag (not "Vite App" or "React App")
- `<html lang="en">` (or appropriate language)

EVERY page generated must include all of the above.

---

## Part 4 — Quick Reference: Vibecode Red Flags

Use this as a final checklist. If your output has 3+ of these, revise before shipping.

| # | Red Flag | Fix |
|---|----------|-----|
| 1 | Primary color is indigo/violet/purple | Pick a different hue |
| 2 | All corners are `rounded-lg` | Vary border-radius across elements |
| 3 | Three equal-width feature cards | Use asymmetric or alternative layout |
| 4 | Inter or Roboto font | Choose a distinctive typeface |
| 5 | Hero → Features → Testimonials skeleton | Design for the content's narrative |
| 6 | Every icon in a colored circle | Remove decorative icons, vary style |
| 7 | "Supercharge/Unlock/Elevate" copy | Write specific, concrete headlines |
| 8 | Pure white `#FFFFFF` background only | Use off-whites, textures, gradients |
| 9 | No hover/focus/empty/error states | Add all interactive states |
| 10 | `<div>` soup, no semantic HTML | Use proper HTML5 elements |
| 11 | Default Tailwind shadows on everything | Create custom shadow scale |
| 12 | No responsive testing | Verify at 375px, 768px, 1280px |
| 13 | Placeholder testimonials (Sarah M.) | Use realistic, specific fake data |
| 14 | `transition-all duration-300` everywhere | Specify properties, vary timing |
| 15 | Missing viewport/OG/favicon meta | Include all meta tags |
| 16 | `p-4` or `p-6` uniform padding | Develop intentional spacing rhythm |
| 17 | No focus indicators | Add visible focus styles |
| 18 | Copyright year is wrong or hardcoded | Use `new Date().getFullYear()` |
| 19 | Default Tailwind color palette | Customize with project-specific tokens |
| 20 | Every section has identical `py-16` | Vary vertical spacing by importance |

---

## Part 5 — The Philosophy

The fundamental problem with vibecoded UI is not that AI wrote it.
It's that AI wrote it *on autopilot*.

Every default choice an LLM makes is the *average* of what it's seen. The average of a
million websites is not a good website — it's a generic one. Vibecoded UI is what happens
when you accept every default, when you let the training data's median taste drive every
decision.

The fix is *intentionality*. A human designer makes choices. They pick THIS shade of green
because it matches the brand's agricultural roots. They use THAT serif font because the
product is about trust and heritage. They leave THIS much whitespace because the content
needs room to breathe.

When generating UI, channel that intentionality. Every color, every font, every spacing
value, every layout decision should be a *choice*, not a *default*. The defaults are the
enemy. Override them with purpose.

The best AI-generated UI is indistinguishable from human-designed UI — not because it
tricks anyone, but because it was built with the same care, the same specificity, and the
same refusal to accept the generic.

Build like you give a damn.
