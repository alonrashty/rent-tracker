# Design Review: London Flat Hunt

---

## 🔴 High Priority

---

### 1. `rent-red` maps to `var(--accent)` in light mode — broken semantic colour

In light mode, `rent-red` is `var(--accent)` = `#0066FF`. That's the same blue used for interactive elements, the focused search border, active drag handles, and price pin hover state. Expensive listings look like links. The dark mode has it right (`#ef5350`); the light mode just forgot to set the colour.

**Fix:** Add a hardcoded light-mode value for `.rent-red` alongside the others:
```css
.rent-green { color: #2e7d32; }
.rent-amber { color: #e65100; }
.rent-red   { color: #c0392b; }  /* explicit; not --accent */
```

---

### 2. Address is the fourth piece of information on the card — wrong hierarchy

Current card order: Price → Beds/baths chips → Commute pills → **Address** → Footer.

Address is the primary identity of a listing. It answers "what is this?" before commute times answer "how is it?". The eye reaches it fourth, after commute data it hasn't yet decided to care about. For a browsing tool this is backwards.

**Fix:** Reorder to: Price + Neighbourhood → Address → Commute pills → Beds/baths → Footer. Commute is a filter signal, not an identifier.

---

### 3. Rent price at 17px is too quiet to anchor the eye

The whole point of triage is rapid price scanning down the feed. At 17px with the neighbourhood label sitting inline on the same baseline, the price doesn't dominate the card body. Compare: the popup renders rent at 20px, which is already better.

**Fix:** Increase card rent to 20–22px. Let the neighbourhood drop to its own line at 12px below the price. This also removes the squeeze problem where a long neighbourhood label ellipsizes to nothing when price is £2,750.

---

### 4. Date chips have no visual treatment — naked text in a card full of chips

Every other metadata element on the card uses `.meta-chip` (background: surface2, 20px radius). The date chips (`.date-chip`) are plain `color: var(--text-muted)` spans — no background, no border. They look like placeholder text next to styled badges.

**Fix:** Either apply `.meta-chip` styling to date chips, or give them a dedicated light background. Consistency is the only goal here.

---

### 5. `<input type="date">` for "Available from" is completely unstyled

The native date picker uses browser chrome that ignores your entire design system — wrong font, wrong border radius, wrong colours. It looks like a bug. It's especially jarring next to the polished pill filters above it.

**Fix:** Style it explicitly:
```css
#avail-from {
  width: 100%;
  padding: 6px 10px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 12px;
}
```

---

### 6. Dismiss button is a 6px-radius square; heart is a circle — paired actions, mismatched shapes

Heart (26px circle) lives at top-right of the photo. Dismiss (24×24, 6px radius — a squarish square) lives at bottom-right of the card body. They're related triage actions buried on opposite ends of the card with no visual relationship. On mobile, reaching dismiss requires a long stretch across the card.

**Fix:** Make dismiss a 24px circle (`border-radius: 50%`) to match heart visually. Consider grouping both actions at the bottom of the card body as a paired row, so triage is done in one place.

---

## 🟡 Medium Priority

---

### 7. Map tile doesn't switch in dark mode despite the code appearing to try

`const dark = window.matchMedia(…).matches` is computed in `initMap()` but then only one tile layer — CartoDB Voyager (light-coloured) — is ever added. In dark mode you get a light-grey map under dark UI. The `dark` variable is computed but never used.

**Fix:** Use `dark_all` vs `voyager` tiles:
```js
const tile = dark
  ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
  : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
L.tileLayer(tile, { … }).addTo(MAP);
```

---

### 8. Sort select has no dropdown indicator — doesn't look interactive

`appearance: none` removes the browser arrow but nothing replaces it. Users see a pill with text and no affordance that it's a select. The label "Sort:" helps, but without the arrow this looks like a static label on desktop.

**Fix:** Add a CSS background arrow:
```css
#sort-select {
  padding-right: 28px;
  background-image: url("data:image/svg+xml,…chevron-down…");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
```
Or drop `appearance: none` and let the browser style it — the native arrow at least communicates affordance.

---

### 9. Map search button icon is a return arrow (↵) — wrong semantics

`&#8629;` is the "carriage return" symbol. It reads as "press Enter" not "search". The adjacent input already handles Enter via `keydown`, so the button is for click.

**Fix:** Replace with a magnifying glass SVG (same 15px size, matching `--text-muted` colour).

---

### 10. "Work N/A" and "LSE N/A" commute pills always render with no data

When commute data isn't enriched, two grey `ct-na` pills say "Work N/A" and "LSE N/A". This is noise: the absence of information communicated as two elements is worse than showing nothing. The commute row takes up a full line with no useful content.

**Fix:** Don't render a pill when the value is null. If both are null, collapse the commute row entirely. If one is present and one isn't, only render the present one.

---

### 11. Five distinct border-radius values in active use — not a system

6px (dismiss), 8px (lightbox nav), 10px (popup buttons), 12px (`--radius`), 18px (popup sheet), 20px (pills). Cards are 12px, popup buttons are 10px, dismiss is 6px — three values for similar-sized elements.

**Fix:** Collapse to three tokens: `--radius-pill: 20px` (all chips/filters), `--radius: 12px` (cards, overlays), `--radius-sm: 8px` (small action buttons). Apply consistently.

---

### 12. Drag handle is a 5px line with no grip affordance

The handle is invisible until hovered — a solid 5px strip that could be confused with a border. No grip dots or lines suggest it's draggable. Users who don't know it exists won't discover it.

**Fix:** Add a subtle 3-dot grip indicator at the vertical centre:
```css
.drag-handle::before {
  content: '⋮';
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  color: var(--text-muted);
  font-size: 14px;
  opacity: 0.5;
}
```

---

### 13. No loading state — the app looks broken for 200–500ms on load

The header shows "Loading…" but the feed area is a white void. There's no skeleton, no spinner, no indication cards are about to appear.

**Fix:** Add 3–4 skeleton cards in the initial HTML that get replaced on first render. CSS-only shimmer with a `@keyframes` animation, no JS needed.

---

### 14. Status badge text renders in raw lowercase

The badge renders `l.status` directly: "new", "favourite", "dismissed". These read as uncapitalized data values, not designed badges.

**Fix:** Capitalize in `buildCard`:
```js
l.status.charAt(0).toUpperCase() + l.status.slice(1)
```

---

### 15. Card body gap is 5px — content rows bleed together visually

The `gap: 5px` between card body rows means five rows of 11–12px text are separated by only 5px. On a small card height this creates a compressed block that the eye struggles to parse into distinct data groups. Commute pills bleed into address bleed into footer.

**Fix:** Use structured grouping rather than uniform gap. Price+address group: 4px gap internally. Then a larger separator (10–12px) before commute pills. Consider wrapping commute and meta chips in a single row if space allows.

---

## 🟢 Low Priority

---

### 16. Photo placeholder uses 🏠 emoji — inconsistent rendering across OS

Emoji rendering varies enough (macOS vs Windows vs Android) that a house emoji looks polished on one platform and blocky on another. The 28px font-size also makes it look oversized in the 148×148 square.

**Fix:** Use a simple SVG building/home icon, same stroke style as the rest of the UI, at 32px, `color: var(--border)`.

---

### 17. Sidebar "Filters" heading is redundant — wasted space

The 10px uppercase "FILTERS" heading appears at the top of the sidebar. The user already knows it's filters. On desktop the heading occupies vertical space that pushes filter controls below the fold.

**Fix:** Remove the heading. The existing group labels (`Max Rent`, `Status`, etc.) already provide structure.

---

### 18. `ct-ok` and `ct-bad` dark mode colours may fail WCAG AA at 11px

`ct-ok` dark: `#7a8ba6` on `#1c2433` — muted blue-grey on dark navy, approximately 3:1 contrast. At 11px/600 weight you need ~4.5:1. `ct-bad` dark: `#a05070` on `#290f1a` — similar concern.

**Fix:** Lighten the foreground colours: `ct-ok-fg` → `#93a8c4`, `ct-bad-fg` → `#c06888` in dark mode. Verify with a contrast checker at 11px/600.

---

### 19. Inline `style=""` attributes on sidebar width, feed width, and sort label

`style="width:240px"` on `<aside>`, `style="width:540px"` on `<div id="feed">`, and a full inline style string on the sort label. These leak layout constants into HTML. The drag-resize JS already overwrites the inline widths, so the initial values should live in CSS.

---

### 20. Lightbox close button is a bare `×` text node — unpolished vs popup close

The popup close button is a styled 30px circle with backdrop blur. The lightbox close is `font-size: 26px` text with padding and 80% opacity — no background, no defined shape. They serve the same function but look like they're from different codebases.

**Fix:** Give the lightbox close the same circular treatment as `.popup-close`:
```css
#lightbox-close {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255,255,255,.15);
  display: flex;
  align-items: center;
  justify-content: center;
}
```
