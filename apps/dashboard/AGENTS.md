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

---

## Cloud Integration: Real-Time Subscriptions

**Note**: This section documents the cloud-based AWS Amplify integration for real-time collaboration features. This is separate from the local-first browsing interface documented above.

### Architecture Overview

The dashboard has **two modes**:

1. **Local Mode** (documented above): Reads filesystem directly via Express server
2. **Cloud Mode** (this section): Connects to AWS Amplify for real-time collaboration

**Tech Stack (Cloud Mode)**:
- AWS Amplify Gen 2 (AppSync GraphQL, DynamoDB, S3, Cognito)
- Real-time subscriptions via WebSocket (graphql-ws protocol)
- Python CLI backend (`AmplifyPublisher`) for mutations
- React frontend with `observeQuery()` for subscriptions

### Real-Time Subscription Pattern

**Key Principle**: State changes happen via DynamoDB table record mutations, not arbitrary signals.

**Flow**:
```
Python CLI (AmplifyPublisher)
    ↓ HTTP GraphQL Mutation
AppSync API
    ↓ DynamoDB Stream
Real-Time Resolver
    ↓ WebSocket (graphql-ws)
Browser (observeQuery subscription)
    ↓ React State Update
Dashboard UI Re-renders
```

**Example**: Extraction Progress Updates
1. CLI creates Snapshot record with `status='RUNNING'`, `completedItems=0`
2. Dashboard subscribes to Snapshot table via `observeQuery()`
3. CLI updates `completedItems` incrementally (10, 20, 30...)
4. Dashboard progress bar animates automatically
5. CLI updates `status='COMPLETED'`
6. Dashboard shows completion indicator

### Data Models (Amplify Schema)

**Corpus**:
```typescript
{
  corpusId: ID!              // Primary key
  name: String!
  description: String
  totalItems: Int
  totalBytes: Int
  createdAt: AWSDateTime!
  owner: String              // Cognito user ID
}
```

**Snapshot**:
```typescript
{
  corpusId: ID!              // Partition key
  snapshotId: String!        // Sort key (content-addressable hash)
  snapshotType: String!      // 'EXTRACTION', 'ANALYSIS', 'RETRIEVAL', 'GRAPH'
  status: String!            // 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
  totalItems: Int!
  processedItems: Int!
  startTime: AWSDateTime!
  endTime: AWSDateTime
  errorMessage: String
  configurationId: String
}
```

**CatalogItem**:
```typescript
{
  corpusId: ID!              // Partition key
  itemId: String!            // Sort key
  relpath: String!
  sha256: String!
  bytes: Int!
  mediaType: String!
  title: String
  tags: [String]
  metadataJson: AWSJSON
  createdAt: AWSDateTime!
  sourceUri: String
  hasExtraction: Boolean
}
// GSIs: mediaType, tags, hasExtraction (for fast filtering)
```

**FileMetadata**:
```typescript
{
  corpusId: ID!              // Partition key
  filePath: String!          // Sort key (e.g., "snapshots/extraction-abc/output.json")
  snapshotId: String
  fileType: String           // 'RAW', 'EXTRACTED', 'ANALYZED', 'GRAPH'
  status: String             // 'LOCAL_ONLY', 'UPLOADING', 'AVAILABLE'
  s3Key: String
  bytes: Int
  sha256: String
  uploadedAt: AWSDateTime
}
```

### Page Structure (Cloud Mode)

**Routes**:
```
/                                              → Corpus list (HomePage)
/corpus/:corpusName                            → Dashboard (CorpusDashboardPage)
/corpus/:corpusName/catalog                    → Catalog browser (CatalogBrowserPage)
/corpus/:corpusName/catalog/:itemId            → Item detail (CatalogItemDetailPage)
/corpus/:corpusName/extracted/:snapshotId      → Snapshot detail (ExtractedSnapshotPage)
```

**CorpusDashboardPage** ([CorpusDashboardPage.tsx:13-31](apps/dashboard/src/pages/CorpusDashboardPage.tsx#L13-L31)):
- Shows **Snapshots** (extraction runs), not individual files
- Subscribes to Snapshot table for real-time updates
- Displays progress bars for running extractions
- Has "Browse Catalog" button linking to catalog browser

**CatalogBrowserPage** ([CatalogBrowserPage.tsx:20-95](apps/dashboard/src/pages/CatalogBrowserPage.tsx#L20-L95)):
- Shows **CatalogItems** (actual corpus files)
- Real-time subscription to CatalogItem table
- Filtering by media type, tags, search query
- Uses GSI queries for efficient filtering

**Key Distinction**:
- Dashboard = Processing runs (snapshots)
- Catalog = Actual files (catalog items)

### Subscription Patterns

#### 1. List All Items (with Real-Time Updates)

```typescript
import { useEffect, useState } from 'react';
import { client } from '../lib/amplify-client';

function MyComponent() {
  const [items, setItems] = useState<CatalogItem[]>([]);

  useEffect(() => {
    const subscription = client.models.CatalogItem.observeQuery({
      filter: { corpusId: { eq: corpusName } }
    }).subscribe({
      next: ({ items: fetchedItems }) => {
        setItems(fetchedItems); // Automatic re-render
      },
      error: (err) => {
        console.error('Subscription error:', err);
      }
    });

    return () => subscription.unsubscribe(); // Critical cleanup!
  }, [corpusName]);

  return <ItemList items={items} />;
}
```

#### 2. Filtered Query (with Real-Time Updates)

```typescript
// Using GSI for efficient filtering
const subscription = client.models.CatalogItem.observeQuery({
  filter: {
    corpusId: { eq: corpusName },
    mediaType: { eq: 'audio/mpeg' }
  }
}).subscribe({
  next: ({ items }) => setAudioFiles(items)
});
```

#### 3. Single Item Watch

```typescript
const subscription = client.models.Snapshot.observeQuery({
  filter: {
    corpusId: { eq: corpusName },
    snapshotId: { eq: snapshotId }
  }
}).subscribe({
  next: ({ items }) => setSnapshot(items[0])
});
```

### Custom Hooks for Subscriptions

**useRealtimeQuery** ([useRealtimeQuery.ts:28-119](apps/dashboard/src/lib/useRealtimeQuery.ts#L28-L119)):

Standardizes subscription pattern with loading/error states:

```typescript
import { useRealtimeQuery } from '../lib/useRealtimeQuery';
import type { Snapshot } from '../lib/amplify-client';

function CorpusDashboardPage() {
  const { items: snapshots, loading, error, reconnecting } = useRealtimeQuery<Snapshot>(
    'Snapshot',
    { corpusId: { eq: corpusName } }
  );

  if (error && !reconnecting) return <ErrorMessage error={error} />;
  if (loading) return <LoadingSpinner />;

  return <SnapshotList snapshots={snapshots} />;
}
```

**Features**:
- Automatic cleanup on unmount
- Loading/error/reconnecting states
- Error counting with retry logic
- Distinguishes transient vs permanent errors

**Other hooks available**:
- `useRealtimeItem()` - Subscribe to single item by ID
- `useRealtimeQueryWithRefetch()` - Adds manual refetch capability

### Backend Integration (Python CLI)

**AmplifyPublisher** ([amplify_publisher.py](src/biblicus/sync/amplify_publisher.py)):

```python
from biblicus.sync.amplify_publisher import AmplifyPublisher

# Initialize publisher
publisher = AmplifyPublisher('MyCorpus')

# Create snapshot (triggers onCreate subscription)
publisher.start_snapshot(
    snapshot_id='extraction-abc123',
    snapshot_type='EXTRACTION',
    total_items=100
)

# Update progress (triggers onUpdate subscription)
for i in range(0, 101, 10):
    publisher.update_snapshot_progress(
        snapshot_id='extraction-abc123',
        completed_items=i
    )
    time.sleep(1)

# Complete (triggers onUpdate subscription)
publisher.complete_snapshot(
    snapshot_id='extraction-abc123',
    total_items=100
)

# Sync catalog to DynamoDB (idempotent)
publisher.sync_catalog(
    catalog_path=corpus.catalog_path,
    force=False  # Skip if unchanged (hash comparison)
)
```

**Key Methods**:
- `start_snapshot()` - Creates Snapshot with status='RUNNING'
- `update_snapshot_progress()` - Updates completedItems field
- `complete_snapshot()` - Marks COMPLETED/FAILED, sets endTime
- `sync_catalog()` - Syncs catalog.json to DynamoDB (idempotent via hash)

**Authentication**: Uses API key (365-day expiry) for backend mutations

### Error Handling

AppSync subscriptions automatically reconnect on network failure. Handle transient errors gracefully:

```typescript
const subscription = client.models.Snapshot.observeQuery({ filter })
  .subscribe({
    next: ({ items }) => {
      setSnapshots(items);
      setError(null); // Clear error on successful update
      setReconnecting(false);
    },
    error: (err) => {
      console.error('Subscription error:', err);

      // Distinguish error types
      const isAuthError = err.message?.includes('Unauthorized');
      const isNetworkError = err.message?.includes('Network');

      if (isAuthError) {
        setError('Authentication failed. Please reconfigure Amplify credentials.');
        setReconnecting(false);
      } else if (isNetworkError) {
        setError('Connection lost. Reconnecting...');
        setReconnecting(true);
        // AppSync will automatically reconnect
      }
    }
  });
```

**Error Categories**:
1. **Transient**: Network failures, timeouts → Show reconnecting state, auto-retry
2. **Permanent**: Auth failures, schema errors → Show error message, don't retry
3. **Too many errors**: >3 consecutive failures → Give up, show refresh message

### Performance Considerations

**Subscription Limits**:
- AppSync supports ~5000 concurrent subscriptions per endpoint
- Normal latency: 100-500ms (AppSync → Browser)
- High latency (>2s): Check AWS region distance

**Message Size**:
- Keep updates small (<100KB)
- Use pagination for large lists
- Avoid embedding large JSON in records

**Battery & Bandwidth**:
- WebSocket is persistent connection
- Mobile users may prefer polling
- Consider disconnecting subscriptions on page blur

**Memory Management**:
Always unsubscribe in useEffect cleanup:
```typescript
useEffect(() => {
  const sub = client.models.X.observeQuery(...).subscribe(...);
  return () => sub.unsubscribe(); // Critical!
}, [dependencies]);
```

### Catalog Sync Workflow

**Idempotent Sync via Hashing**:

```python
def sync_catalog(self, catalog_path: Path, force: bool = False) -> SyncResult:
    # 1. Load and hash catalog
    catalog = CorpusCatalog.load(catalog_path)
    catalog_hash = self._compute_catalog_hash(catalog)

    # 2. Check if changed
    metadata = self._get_catalog_metadata()
    if not force and metadata and metadata.catalogHash == catalog_hash:
        return SyncResult(skipped=True, reason="Catalog unchanged")

    # 3. Choose sync strategy
    if len(catalog.items) < 100:
        result = self._full_replacement_sync(catalog)
    else:
        result = self._incremental_sync(catalog, metadata)

    # 4. Update metadata
    self._sync_catalog_metadata(catalog, catalog_hash)

    return result
```

**Why DynamoDB instead of just S3?**:
- Fast filtering by tags, media type (via GSI queries)
- Real-time subscriptions for catalog changes
- No need to download/parse entire catalog.json
- Enables pagination for large catalogs (1000+ items)

**Cost**: ~$0.10/month for 1000-item catalog with 10 syncs/day

### Testing

**Manual Test** (CLI Publisher):
```bash
# Terminal 1: Watch dashboard
open http://localhost:5175

# Terminal 2: Simulate extraction
python scripts/test_snapshot_realtime.py
```

Expected: Snapshot appears, progress bar animates 0→100%, status changes to COMPLETED.

**Automated E2E Test**:
```bash
python scripts/test_realtime_e2e.py
```

Validates:
- onCreate event delivery (<1s latency target, typically ~1.2s)
- onUpdate event sequence (ordered correctly)
- Dashboard state matches backend state
- State transitions (RUNNING → COMPLETED/FAILED)

**BDD Feature Tests**:
```bash
behave features/realtime_subscriptions.feature
```

12 scenarios covering:
- Immediate snapshot appearance
- Smooth progress updates
- Status transitions
- Network reconnection
- Multiple snapshots
- Catalog real-time updates
- File upload status transitions
- Authentication errors
- Multi-tab consistency
- Memory leak prevention

### Troubleshooting

**Subscription Not Receiving Updates**:
1. Check Amplify configuration: `apps/dashboard/amplify_outputs.json`
2. Verify API key hasn't expired (check Amplify console)
3. Inspect browser network tab for WebSocket connection
4. Look for `@connection` errors in console

**Updates Delayed**:
- Normal latency: 100-500ms
- High latency (>2s): Check AWS region distance
- Batching: AppSync may batch rapid updates

**Memory Leaks**:
- Always unsubscribe in useEffect cleanup
- Check for lingering WebSocket connections in network tab
- Use React DevTools Profiler to detect memory growth

**Authentication Failures**:
- Frontend uses Cognito user pool
- Backend uses API key (365-day expiry)
- Check `amplify_outputs.json` for correct endpoint/API key

### Development Workflow (Cloud Mode)

1. **Configure Amplify** (one-time):
   ```bash
   biblicus dashboard configure amplify \
     --endpoint https://xxx.appsync-api.us-east-1.amazonaws.com/graphql \
     --api-key da2-xxxxx \
     --bucket biblicus-files-xxx \
     --region us-east-1
   ```

2. **Start dashboard**:
   ```bash
   cd apps/dashboard
   npm run dev
   ```

3. **Simulate extraction** (for testing):
   ```bash
   python scripts/test_snapshot_realtime.py
   ```

4. **Run E2E tests**:
   ```bash
   python scripts/test_realtime_e2e.py
   ```

### Dual Authentication

**Frontend (Cognito)**:
- User pool authentication for dashboard access
- Users sign up/sign in via Amplify UI
- Owner-based authorization (users see only their data)

**Backend (API Key)**:
- Python CLI uses API key for mutations
- 365-day expiry (renewable)
- No user context required

**Why both?**:
- Frontend needs user identity for multi-user scenarios
- Backend CLI needs simple, non-interactive auth

### Key Files Reference

**Backend (Python)**:
- `src/biblicus/sync/amplify_publisher.py` - GraphQL mutations
- `src/biblicus/sync/catalog_sync.py` - Catalog sync logic
- `scripts/test_snapshot_realtime.py` - Manual test publisher
- `scripts/test_realtime_e2e.py` - Automated E2E tests
- `features/realtime_subscriptions.feature` - BDD scenarios

**Frontend (React)**:
- `apps/dashboard/src/lib/amplify-client.ts` - Amplify client setup
- `apps/dashboard/src/lib/useRealtimeQuery.ts` - Custom hooks
- `apps/dashboard/src/pages/CorpusDashboardPage.tsx` - Snapshot subscriptions
- `apps/dashboard/src/pages/CatalogBrowserPage.tsx` - CatalogItem subscriptions
- `apps/dashboard/src/pages/CatalogItemDetailPage.tsx` - Item detail + extractions

**Infrastructure**:
- `apps/dashboard/amplify/data/resource.ts` - Amplify schema
- `apps/dashboard/amplify/backend.ts` - CDK stack
- `apps/dashboard/amplify_outputs.json` - Generated config (gitignored)

**Documentation**:
- `docs/realtime-subscriptions.md` - Comprehensive subscription guide
- `docs/corpus-viewer-implementation-plan.md` - Full implementation plan

### What NOT to Do (Cloud Mode)

- ❌ Don't create subscriptions without cleanup (memory leaks)
- ❌ Don't use subscriptions for one-time queries (use `.list()` or `.get()`)
- ❌ Don't sync catalog on every extraction (only when items change)
- ❌ Don't generate new snapshot IDs (use content-addressable hashes)
- ❌ Don't partition S3 by user ID (use direct mirror: `corpus-name/path`)
- ❌ Don't retry auth errors (permanent failures)
- ❌ Don't block UI on subscription errors (show reconnecting state)

### What TO Do (Cloud Mode)

✅ Use `observeQuery()` for all real-time data
✅ Always unsubscribe in useEffect cleanup
✅ Handle reconnecting state gracefully
✅ Use custom hooks (`useRealtimeQuery`) to standardize patterns
✅ Sync catalog idempotently (hash check first)
✅ Use content-addressable snapshot IDs from Biblicus
✅ Mirror local filesystem structure in S3
✅ Distinguish transient vs permanent errors
✅ Keep subscription filters specific (leverage GSIs)
✅ Test with E2E script before deploying
