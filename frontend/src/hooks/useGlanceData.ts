import { useState, useEffect, useRef } from 'react';
import { GlanceData } from '../types';

const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

interface UseGlanceDataResult {
  data: GlanceData | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useGlanceData(): UseGlanceDataResult {
  const [data, setData] = useState<GlanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = async () => {
    try {
      const res = await fetch('/api/glance');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const json: GlanceData = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    intervalRef.current = setInterval(fetchData, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return { data, loading, error, refresh: fetchData };
}
