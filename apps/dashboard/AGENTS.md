# Biblicus Dashboard (Project Memory)

## What we're building

A **local-first corpus viewer** that reads Biblicus corpora directly from the filesystem and displays them with a **gratuitously animated, Bauhaus-inspired interface**.

## Core Design Principles

### Animation-First Interface

- **GSAP is fundamental**: Every interaction should use GSAP animations
- **Constantly moving**: UI elements should feel alive and dynamic
- **Panel-based, not page-based**: Horizontal sliding panels instead of router-based pages
- **Progressive disclosure**: Left to right = general to specific (Aggregate → Tree → Viewer)
- **Slide from right**: New content slides in from the right when selected

### Bauhaus Visual Design

- **Flat, minimal aesthetic**: No shadows, borders, gradients, or shading
- **Consistent rounded corners**: All rectangles use consistent border radius (1.5rem-3.5rem)
- **Flat colors only**: Pure colors without gradients or effects
- **Clean typography**: Sans-serif, clear hierarchy
- **Whitespace**: Generous spacing, not cluttered

### User Mental Model

- **No "catalog" terminology**: Users think of corpora as "folders full of files"
- **Progressive enhancement**: Show whatever data is available, skip what's missing
- **Fail gracefully**: Missing metadata should not break the interface
- **Direct browsing**: No syncing, no cloud, just local filesystem

## Architecture

### Three-Panel Layout

1. **Aggregate Panel (Left)**: Always visible, shows statistics
   - Total files, total size, average size
   - Media type distribution
   - Tag distribution
   - Colored, rounded cards with stagger animation

2. **File Tree Panel (Center)**: Slides in when corpus selected
   - Hierarchical file tree
   - Search functionality
   - Click to select files
   - Animated appearance

3. **Content Viewer Panel (Right)**: Slides in when file selected
   - Pluggable viewer system
   - Different viewers for different content types
   - Metadata display
   - Close button to slide out

### Technology Stack

- **Frontend**: React + TypeScript + Vite
- **Styling**: TailwindCSS (configured for Bauhaus design)
- **Animation**: GSAP + @gsap/react
- **Backend**: Local Express server reading filesystem
- **No routing**: Component state drives panel visibility

## Data Strategy

### Graceful Progressive Enhancement

**CRITICAL**: The dashboard must handle incomplete or missing data gracefully.

- **Metadata folder location**: `<corpus>/metadata/catalog.json`
- **If metadata missing**: Display what we can (file listing, basic stats)
- **Never fail completely**: Always show something useful
- **Progressive disclosure**: Add information as it becomes available
- **No error walls**: Partial data is better than no data

### What to display when data is incomplete

- **No catalog**: Show raw file listing from filesystem
- **No metadata**: Show filename, size, type (guessed from extension)
- **No statistics**: Skip aggregate panel or show basic counts
- **No extraction artifacts**: Display raw file metadata only

## Coding Policies

### NO Backward Compatibility (Critical)

- **Never support multiple locations**: Use ONLY `metadata/catalog.json`
- **No fallback checks**: Don't check `.biblicus/` then `metadata/`
- **No "try both ways"**: One correct implementation only
- **Fail gracefully instead**: If data missing, show what you can

### Animation Standards

- **Every panel transition**: Use slideInFromRight/slideOutToRight
- **List appearances**: Use fadeInStagger with 0.05-0.08s stagger
- **Coordinated animations**: Use GSAP timelines for multi-element sequences
- **Smooth curves**: Use 'power3.out' easing by default
- **Duration consistency**: 0.6s for most transitions

### Component Structure

```
src/
├── lib/
│   ├── animations.ts        # GSAP animation helpers
│   └── local-api.ts         # Backend API client
├── components/
│   └── viewer/
│       ├── Panel.tsx        # Reusable animated panel
│       ├── ViewerShell.tsx  # 3-panel orchestrator
│       ├── AggregatePanel.tsx
│       ├── FileTreePanel.tsx
│       └── ContentViewerPanel.tsx
└── pages/
    └── HomePage.tsx         # Corpus grid + ViewerShell
```

### Styling Guidelines

- **No inline styles**: Use Tailwind utility classes
- **Rounded corners**: Use `rounded-3xl`, `rounded-2xl`, etc.
- **No shadows**: TailwindCSS configured to remove all shadows
- **Color backgrounds**: Use `bg-blue-100`, `bg-green-100`, etc. for cards
- **Responsive**: Use `md:` and `lg:` breakpoints appropriately

## Backend API

### Local Express Server

**Location**: `apps/dashboard/server.js`

**Endpoints**:
- `GET /api/corpora` - List all corpora (finds folders with metadata or .biblicus)
- `GET /api/corpora/:name` - Get corpus details
- `GET /api/corpora/:name/catalog` - Get catalog items (with filters)
- `GET /api/corpora/:name/catalog/:itemId` - Get specific item
- `GET /api/corpora/:name/snapshots` - List extraction snapshots
- `GET /api/config` - Get corpora root path
- `POST /api/config` - Set corpora root path

**Behavior**:
- Reads directly from filesystem (no database)
- Security: Path validation to prevent traversal
- Graceful failures: Return empty arrays or null when data missing
- CORS enabled for local development

## Development Workflow

1. **Animation library** (`lib/animations.ts`) provides GSAP helpers
2. **Panel component** handles animation lifecycle
3. **ViewerShell** orchestrates panel visibility and transitions
4. **Individual panels** focus on their specific content
5. **HomePage** manages corpus selection state

## What NOT to Do

- ❌ Don't use React Router for corpus/file navigation
- ❌ Don't add page-based layouts
- ❌ Don't use shadows, borders, or gradients
- ❌ Don't show "catalog" terminology to users
- ❌ Don't implement backward compatibility
- ❌ Don't fail completely when data is missing
- ❌ Don't sync to cloud/DynamoDB for local browsing
- ❌ Don't create heavy abstractions for simple tasks

## What TO Do

✅ Use GSAP for all animations
✅ Use panel-based layout with horizontal sliding
✅ Apply Bauhaus design consistently
✅ Show "files" and "statistics" to users
✅ Implement ONE correct approach cleanly
✅ Display what you can, skip what's missing
✅ Read directly from local filesystem
✅ Keep components focused and simple
