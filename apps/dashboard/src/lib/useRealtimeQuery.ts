import { useEffect, useState, useRef } from 'react';
import { client } from './amplify-client';

/**
 * Custom hook for real-time subscriptions with error handling and loading states.
 *
 * This hook wraps Amplify's observeQuery() to provide a standardized interface
 * for real-time data subscriptions with automatic cleanup, error handling, and
 * loading indicators.
 *
 * @template T The type of items returned by the query
 * @param modelName The name of the Amplify model to query (e.g., 'Snapshot', 'CatalogItem')
 * @param filter GraphQL filter object to apply to the query
 * @returns Object containing items, loading state, and any errors
 *
 * @example
 * ```typescript
 * const { items: snapshots, loading, error } = useRealtimeQuery<Snapshot>(
 *   'Snapshot',
 *   { corpusId: { eq: 'Alfa' } }
 * );
 *
 * if (error) return <ErrorMessage error={error} />;
 * if (loading) return <LoadingSpinner />;
 * return <SnapshotList snapshots={snapshots} />;
 * ```
 */
export function useRealtimeQuery<T>(
  modelName: keyof typeof client.models,
  filter: any
): {
  items: T[];
  loading: boolean;
  error: Error | null;
  reconnecting: boolean;
} {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [reconnecting, setReconnecting] = useState(false);

  // Track subscription to avoid double subscriptions
  const subscriptionRef = useRef<any>(null);
  const errorCountRef = useRef(0);

  useEffect(() => {
    // Cancel existing subscription if any
    if (subscriptionRef.current) {
      subscriptionRef.current.unsubscribe();
      subscriptionRef.current = null;
    }

    // Create new subscription
    try {
      const model = client.models[modelName] as any;

      if (!model || !model.observeQuery) {
        throw new Error(`Model ${String(modelName)} does not support observeQuery()`);
      }

      subscriptionRef.current = model
        .observeQuery({ filter })
        .subscribe({
          next: ({ items: fetchedItems }: { items: T[] }) => {
            setItems(fetchedItems);
            setLoading(false);
            setError(null);
            setReconnecting(false);
            errorCountRef.current = 0; // Reset error count on success
          },
          error: (err: Error) => {
            errorCountRef.current++;

            console.error(`Subscription error (${String(modelName)}):`, err);

            // Distinguish between transient and permanent errors
            const isAuthError = err.message?.includes('Unauthorized') ||
                               err.message?.includes('Not Authorized');
            const isNetworkError = err.message?.includes('Network') ||
                                  err.message?.includes('timeout');

            if (isAuthError) {
              // Permanent error - don't retry
              setError(new Error(
                'Authentication failed. Please reconfigure Amplify credentials.'
              ));
              setLoading(false);
              setReconnecting(false);
            } else if (isNetworkError || errorCountRef.current < 3) {
              // Transient error - show reconnecting state
              setError(new Error('Connection lost. Reconnecting...'));
              setReconnecting(true);
              // AppSync will automatically reconnect
            } else {
              // Too many errors - give up
              setError(new Error(
                'Unable to establish subscription. Please refresh the page.'
              ));
              setLoading(false);
              setReconnecting(false);
            }
          },
        });
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }

    // Cleanup subscription on unmount or dependency change
    return () => {
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
    };
  }, [modelName, JSON.stringify(filter)]);

  return { items, loading, error, reconnecting };
}

/**
 * Hook for subscribing to a single item by ID.
 *
 * @template T The type of item returned by the query
 * @param modelName The name of the Amplify model
 * @param id The ID of the item to watch
 * @returns Object containing the item, loading state, and any errors
 *
 * @example
 * ```typescript
 * const { item: snapshot, loading, error } = useRealtimeItem<Snapshot>(
 *   'Snapshot',
 *   { corpusId: 'Alfa', snapshotId: 'extraction-123' }
 * );
 * ```
 */
export function useRealtimeItem<T>(
  modelName: keyof typeof client.models,
  id: Record<string, string>
): {
  item: T | null;
  loading: boolean;
  error: Error | null;
  reconnecting: boolean;
} {
  // Convert ID object to filter
  const filter = Object.fromEntries(
    Object.entries(id).map(([key, value]) => [key, { eq: value }])
  );

  const { items, loading, error, reconnecting } = useRealtimeQuery<T>(
    modelName,
    filter
  );

  return {
    item: items.length > 0 ? items[0] : null,
    loading,
    error,
    reconnecting,
  };
}

/**
 * Hook that provides a callback for manually refetching data.
 *
 * Useful when you need to force a refresh in addition to automatic updates.
 *
 * @template T The type of items returned by the query
 * @param modelName The name of the Amplify model
 * @param filter GraphQL filter object
 * @returns Object containing items, loading, error, and refetch function
 *
 * @example
 * ```typescript
 * const { items, loading, error, refetch } = useRealtimeQueryWithRefetch<CatalogItem>(
 *   'CatalogItem',
 *   { corpusId: { eq: corpusName } }
 * );
 *
 * // Force refresh when user clicks button
 * <button onClick={refetch}>Refresh</button>
 * ```
 */
export function useRealtimeQueryWithRefetch<T>(
  modelName: keyof typeof client.models,
  filter: any
): {
  items: T[];
  loading: boolean;
  error: Error | null;
  reconnecting: boolean;
  refetch: () => Promise<void>;
} {
  const result = useRealtimeQuery<T>(modelName, filter);
  const [refetching, setRefetching] = useState(false);

  const refetch = async () => {
    try {
      setRefetching(true);

      const model = client.models[modelName] as any;
      const { data } = await model.list({ filter });

      // Update items immediately (subscription will continue after)
      result.items.splice(0, result.items.length, ...data);
    } catch (err) {
      console.error('Refetch failed:', err);
    } finally {
      setRefetching(false);
    }
  };

  return {
    ...result,
    loading: result.loading || refetching,
    refetch,
  };
}
