# Real-Time Subscriptions in Biblicus Dashboard

## Overview

Amplify Gen 2 provides automatic real-time updates via AppSync subscriptions. When the Python CLI creates or updates DynamoDB records, the dashboard receives WebSocket events and re-renders automatically—no polling required.

This document explains how to use real-time subscriptions in Biblicus, with examples for both backend (Python) and frontend (React) code.

## Architecture

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

**Key Components:**
- **Backend (Python)**: Makes HTTP GraphQL mutations to create/update records
- **AppSync**: Automatically publishes DynamoDB changes to WebSocket subscribers
- **Frontend (React)**: Subscribes via `observeQuery()` and receives real-time updates
- **No Custom Code**: WebSocket infrastructure provided by Amplify Gen 2

## Pattern: State Changes via Table Records

**Key Principle**: State changes happen via record mutations, not arbitrary signals.

Instead of sending custom "snapshot started" or "progress update" messages, we create/update database records. AppSync automatically notifies subscribers of these changes via `onCreate`, `onUpdate`, and `onDelete` events.

### Example: Extraction Progress

1. **CLI creates Snapshot** with `status='RUNNING'`, `completedItems=0`
   - Triggers `onCreate` subscription event
   - Dashboard sees new snapshot appear

2. **Dashboard subscribes** to Snapshot changes via `observeQuery()`
   - Automatically receives all future updates

3. **CLI updates** `completedItems` incrementally (10, 20, 30...)
   - Each update triggers `onUpdate` subscription event
   - Dashboard progress bar animates automatically

4. **CLI updates** `status='COMPLETED'`
   - Triggers final `onUpdate` event
   - Dashboard shows completion indicator

**This pattern comes "for free" from Amplify Gen 2**—no custom WebSocket infrastructure needed.

## Implementation Examples

### Backend (Python)

```python
from biblicus.sync.amplify_publisher import AmplifyPublisher

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
```

**How it works:**
- `start_snapshot()` executes a GraphQL `createSnapshot` mutation
- `update_snapshot_progress()` executes `updateSnapshot` mutation
- AppSync automatically pushes these changes to WebSocket subscribers
- No WebSocket code needed in Python—just HTTP mutations

### Frontend (React)

```typescript
import { useEffect, useState } from 'react';
import { client } from '../lib/amplify-client';
import type { Snapshot } from '../lib/amplify-client';

function CorpusDashboardPage() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);

  useEffect(() => {
    // observeQuery returns subscription that receives:
    // - onCreate: new snapshot appears
    // - onUpdate: progress/status changes
    // - onDelete: snapshot removed
    const subscription = client.models.Snapshot.observeQuery({
      filter: { corpusId: { eq: corpusName } }
    }).subscribe({
      next: ({ items }) => {
        setSnapshots(items); // Automatic re-render
      },
      error: (err) => {
        console.error('Subscription error:', err);
      }
    });

    return () => subscription.unsubscribe();
  }, [corpusName]);

  return (
    <div>
      {snapshots.map(snapshot => (
        <ProgressBar
          key={snapshot.snapshotId}
          current={snapshot.completedItems}
          total={snapshot.totalItems}
          status={snapshot.status}
        />
      ))}
    </div>
  );
}
```

**How it works:**
- `observeQuery()` establishes WebSocket connection to AppSync
- Returns all matching records initially
- Automatically receives updates when records change
- Component re-renders with latest data
- Unsubscribes on component unmount

## Subscription Patterns

### 1. List All Items (with Real-Time Updates)

Subscribe to all catalog items for a corpus:

```typescript
client.models.CatalogItem.observeQuery({
  filter: { corpusId: { eq: corpusName } }
}).subscribe({
  next: ({ items }) => setItems(items)
});
```

**Use case**: Catalog browser that shows new items as they're ingested

### 2. Filtered Query (with Real-Time Updates)

Subscribe only to items matching specific criteria:

```typescript
client.models.FileMetadata.observeQuery({
  filter: {
    corpusId: { eq: corpusName },
    status: { eq: 'UPLOADING' }
  }
}).subscribe({
  next: ({ items }) => setUploadingFiles(items)
});
```

**Use case**: Upload progress tracker showing only in-progress uploads

### 3. Single Item Watch

Subscribe to updates for a specific snapshot:

```typescript
client.models.Snapshot.observeQuery({
  filter: {
    corpusId: { eq: corpusName },
    snapshotId: { eq: snapshotId }
  }
}).subscribe({
  next: ({ items }) => setSnapshot(items[0])
});
```

**Use case**: Snapshot detail page showing real-time progress

### 4. Secondary Index Query

Use GSI for efficient filtered subscriptions:

```typescript
// Requires GSI defined in schema
client.models.CatalogItem.itemsByMediaType({
  mediaType: 'application/pdf',
  corpusId: corpusName
}).subscribe({
  next: ({ items }) => setPdfItems(items)
});
```

**Use case**: Media-type filtered catalog view

## Error Handling

AppSync subscriptions automatically reconnect on network failure. Handle transient errors gracefully:

```typescript
const subscription = client.models.Snapshot.observeQuery({ filter })
  .subscribe({
    next: ({ items }) => {
      setSnapshots(items);
      setError(null); // Clear error on successful update
    },
    error: (err) => {
      console.error('Subscription error:', err);
      setError('Connection lost. Retrying...');
      // AppSync will automatically reconnect
      // Show user-friendly message while reconnecting
    }
  });
```

**Best practices:**
- Always clear error state on successful `next()` callback
- Show user-friendly reconnection messages
- Don't retry manually—AppSync handles reconnection
- Log errors for debugging but don't throw

## Performance Considerations

### Subscription Limits
- AppSync supports **~5000 concurrent subscriptions** per endpoint
- Each browser tab = 1 subscription per `observeQuery()` call
- Typical usage: 3-5 subscriptions per page = 1000 concurrent users

### Message Size
- Keep updates **small (<100KB)**
- Use pagination for large lists
- Avoid storing large blobs in DynamoDB (use S3 + reference)

### Bandwidth
- WebSocket is persistent—uses more bandwidth than polling
- Consider polling for mobile users on metered connections
- Subscription uses ~1-5KB/minute when idle (keep-alives)

### Battery Impact
- Subscriptions use **more battery** than on-demand polling
- Mobile browsers may throttle WebSocket connections
- Consider auto-pause subscriptions when tab is backgrounded

### Optimization Tips
1. **Minimize subscriptions**: Combine filters when possible
2. **Use GSIs**: Avoid client-side filtering of large result sets
3. **Pagination**: Use `limit` and `nextToken` for large catalogs
4. **Conditional rendering**: Only render visible items

## Testing

### Manual Test (CLI Publisher)

Test real-time updates by simulating an extraction:

```bash
# Terminal 1: Watch dashboard
cd apps/dashboard && npm run dev
open http://localhost:5175

# Terminal 2: Simulate extraction
python scripts/test_snapshot_realtime.py
```

**Expected behavior:**
1. New snapshot appears within 1 second
2. Progress bar animates from 0→100%
3. Status changes to COMPLETED
4. All updates smooth and immediate

### Automated Test (E2E)

Run end-to-end subscription tests:

```bash
python scripts/test_realtime_e2e.py
```

**Validates:**
- onCreate event delivery latency (<1s)
- onUpdate event sequence (ordered correctly)
- Dashboard state matches backend state
- Error recovery after network disconnection

## Troubleshooting

### Subscription Not Receiving Updates

**Symptoms:** Dashboard doesn't update when CLI makes changes

**Diagnosis:**
1. Check Amplify configuration: `apps/dashboard/amplify_outputs.json`
   ```bash
   cat apps/dashboard/amplify_outputs.json | jq '.data.url'
   ```
2. Verify API key hasn't expired (check Amplify console)
3. Inspect browser network tab for WebSocket connection
   - Look for `wss://` connection to AppSync
   - Should show as "101 Switching Protocols"
4. Check console for `@connection` errors

**Solutions:**
- Regenerate outputs: `npx ampx generate outputs --branch main --app-id <app-id>`
- Restart dev server: `npm run dev`
- Clear browser cache and reload

### Updates Delayed

**Symptoms:** Changes take 2-5 seconds to appear in dashboard

**Normal latency:** 100-500ms (AppSync → Browser)

**High latency (>2s):**
- Check AWS region distance (cross-region adds latency)
- Verify no network throttling (VPN, corporate firewall)
- AppSync may batch rapid updates (intentional for performance)

**Solutions:**
- Use same AWS region as AppSync endpoint
- Disable network throttling in dev tools
- Reduce update frequency in CLI (batch progress updates)

### Memory Leaks

**Symptoms:** Browser tab memory grows over time, eventually slows down

**Cause:** Forgot to unsubscribe in `useEffect` cleanup

**Solution:** Always unsubscribe in cleanup function:

```typescript
useEffect(() => {
  const sub = client.models.Snapshot.observeQuery(...).subscribe(...);
  return () => sub.unsubscribe(); // Critical!
}, [dependencies]);
```

**Validation:**
- Open Chrome DevTools → Memory → Take heap snapshot
- Look for growing number of `Subscription` objects
- Should see 1 subscription per `observeQuery()` call, not accumulating

### Authentication Errors

**Symptoms:** `"Not Authorized to access..."` errors in console

**Cause:** Wrong authorization mode or expired credentials

**Solutions:**
- **Frontend (browser)**: Use Cognito user pool authentication
- **Backend (Python CLI)**: Use API key authentication
- Verify `amplify/data/resource.ts` has dual auth:
  ```typescript
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
    apiKeyAuthorizationMode: { expiresInDays: 365 }
  }
  ```
- Check API key expiration in Amplify console

### WebSocket Disconnections

**Symptoms:** Subscription stops working after 5-10 minutes

**Cause:** Network timeout, browser throttling, or AppSync connection limit

**Normal behavior:** AppSync automatically reconnects

**Monitor reconnections:**
```typescript
let reconnectCount = 0;

const subscription = client.models.Snapshot.observeQuery({ filter })
  .subscribe({
    next: ({ items }) => {
      console.log(`Received update (reconnect count: ${reconnectCount})`);
      setSnapshots(items);
    },
    error: (err) => {
      reconnectCount++;
      console.error(`Disconnected (attempt ${reconnectCount}):`, err);
    }
  });
```

**When to worry:**
- Reconnections every few seconds (check network stability)
- Reconnections never succeed (check auth, API key)

## Advanced Patterns

### Optimistic Updates

Show changes immediately, then reconcile with server:

```typescript
function addItem(item: CatalogItem) {
  // Show immediately
  setItems(prev => [...prev, item]);

  // Send to server
  client.models.CatalogItem.create({ input: item }).then(() => {
    // Subscription will reconcile actual server state
  }).catch(err => {
    // Revert optimistic update on error
    setItems(prev => prev.filter(i => i.itemId !== item.itemId));
  });
}
```

### Pagination with Real-Time

Combine pagination with subscriptions for large catalogs:

```typescript
const [items, setItems] = useState<CatalogItem[]>([]);
const [nextToken, setNextToken] = useState<string | null>(null);

// Initial load with pagination
useEffect(() => {
  client.models.CatalogItem.list({
    filter: { corpusId: { eq: corpusName } },
    limit: 50,
    nextToken: nextToken
  }).then(({ data, nextToken: next }) => {
    setItems(prev => [...prev, ...data]);
    setNextToken(next);
  });
}, [corpusName, nextToken]);

// Real-time updates for new items
useEffect(() => {
  const subscription = client.models.CatalogItem.observeQuery({
    filter: {
      corpusId: { eq: corpusName },
      createdAt: { gt: new Date().toISOString() } // Only new items
    }
  }).subscribe({
    next: ({ items: newItems }) => {
      setItems(prev => [...newItems, ...prev]); // Prepend new items
    }
  });

  return () => subscription.unsubscribe();
}, [corpusName]);
```

### Conditional Subscriptions

Enable/disable subscriptions based on user preference:

```typescript
function useConditionalSubscription(enabled: boolean) {
  const [items, setItems] = useState<Snapshot[]>([]);

  useEffect(() => {
    if (!enabled) {
      // Poll instead
      const interval = setInterval(() => {
        client.models.Snapshot.list({ filter }).then(({ data }) => {
          setItems(data);
        });
      }, 5000);

      return () => clearInterval(interval);
    }

    // Subscribe for real-time
    const sub = client.models.Snapshot.observeQuery({ filter })
      .subscribe({ next: ({ items }) => setItems(items) });

    return () => sub.unsubscribe();
  }, [enabled]);

  return items;
}
```

## Related Documentation

- [Corpus Viewer Implementation Plan](corpus-viewer-implementation-plan.md) - Overall architecture
- [AmplifyPublisher API Reference](../src/biblicus/sync/amplify_publisher.py) - Backend Python API
- [Amplify Gen 2 Documentation](https://docs.amplify.aws/gen2/) - Official Amplify docs
- [AppSync Real-Time](https://docs.aws.amazon.com/appsync/latest/devguide/aws-appsync-real-time-data.html) - AWS AppSync details

## Summary

**Key Takeaways:**
1. State changes via DynamoDB records trigger automatic WebSocket updates
2. Backend uses HTTP mutations only (no WebSocket code)
3. Frontend uses `observeQuery()` for automatic subscriptions
4. AppSync handles reconnection, batching, and scaling automatically
5. Pattern comes "for free" from Amplify Gen 2

**When to use subscriptions:**
- Dashboard views showing live progress
- Catalog browsers with real-time item addition
- Collaborative features requiring immediate updates

**When to use polling:**
- Mobile apps with battery concerns
- Infrequent updates (<1/minute)
- Large result sets (>1000 items) with heavy filtering
