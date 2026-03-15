# Stack Navigation Animation Brief (Sub-Agent Task)

## Goal
Build a simplified, isolated demo that proves a reusable UI/animation model for stack-based navigation. The demo must focus only on the animation and layout behavior, decoupled from the current app logic and data fetching.

This demo will become the reference for a reusable framework that:
- Mirrors breadcrumb hierarchy in the URL.
- Moves items from a content list/grid into the breadcrumb stack.
- Handles push/pop transitions with deterministic, smooth motion.

## Core Model (Data Structure)
Define a single source of truth for navigation state:

- `stack`: ordered list of nodes representing the breadcrumb hierarchy.
- The stack is mirrored in the URL (e.g., `/corpora/<name>/items/<id>`).
- The stack behaves like a DOM tree: inserting or removing a node automatically updates the rendered breadcrumb list and content areas.
- A push inserts a node at the end of the stack; a pop removes one or more nodes from the end.

## UI Layout Model
The UI must always render:

1) **Breadcrumb List (Top)**
   - Visualizes `stack` as a linear breadcrumb row.
   - The breadcrumb row represents the stack order exactly.

2) **Content Stack (Below)**
   - A horizontal stack of content panels, one per stack level.
   - Panels slide left/right as the stack changes.
   - The panel for the active stack node is centered; deeper nodes appear to the right when drilling down.

## Animation Rules
### Push (Drill Down)
- The next content panel slides in **from the right**.
- The previous panel slides left off-screen (or remains partially visible if desired), but this is not an "outgoing" animation.
- **Do not run a "leave" animation** for the outgoing panel during drill-down.
- The selected list item should move into the breadcrumb list.

### Pop (Go Up)
- Pop transitions are explicit:
  - The outgoing breadcrumb is removed.
  - The outgoing content panel slides right (out of view).
  - Only during pop should we run exit animations.

### Breadcrumb Morph
- Selected list item morphs into its breadcrumb slot.
- Shell and content must move together with no desync.
- No duplicate cards visible during morph.

## Deep-Link Drill-Down (Beat Sequence)
When loading a deep link (e.g., `/corpora/<name>/items/<id>`):
- Start from root in the UI (even if data is cached).
- Show each level for a full beat.
- Animate to the next level over a beat.
- Repeat until the full stack is reached.

## Demo Requirements
1) A small, isolated page (no dependencies on app routing or data).
2) Hard-coded sample data for 3+ stack levels.
3) Controls for:
   - Push next level
   - Pop level
   - Load a deep link (simulate full stack)
4) Logs or simple visual markers for current stack state.

## Non-Goals
- No backend, no real data fetching.
- No integration with the existing app’s state.
- No styling polish beyond what’s needed to validate the motion model.

## Success Criteria
The demo must:
- Show smooth, deterministic movement of an item from list/grid to breadcrumb.
- Avoid layout jiggle or snapping.
- Use a single stack state to drive both breadcrumbs and panels.
- Cleanly support push/pop and deep-link drill-down timing.
