import { useState, useEffect } from 'react';
import { CalendarEvent } from '../types';

function getStartOfCurrentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
}

interface CalendarData {
  events: CalendarEvent[];
  loading: boolean;
  error: boolean;
}

export function useCalendarData(): CalendarData {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fromDate = getStartOfCurrentMonth();
    fetch(`/api/calendar?days=45&from_date=${fromDate}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => setEvents(data.events ?? []))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return { events, loading, error };
}
