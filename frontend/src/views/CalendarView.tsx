import { useState, useEffect } from 'react';
import { CalendarEvent } from '../types';
import { useCalendarData } from '../hooks/useCalendarData';
import styles from './CalendarView.module.css';

type CalView = 'daily' | 'weekly' | 'monthly';

const DAY_NAMES_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const DAY_NAMES_HEADER = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

// ── Helpers ─────────────────────────────────────────────────────────────────

function toDateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isToday(d: Date): boolean {
  const t = new Date();
  return d.getFullYear() === t.getFullYear() &&
    d.getMonth() === t.getMonth() &&
    d.getDate() === t.getDate();
}

function getWeekDates(): Date[] {
  const today = new Date();
  const sunday = new Date(today);
  sunday.setDate(today.getDate() - today.getDay());
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(sunday);
    d.setDate(sunday.getDate() + i);
    return d;
  });
}

function getMonthDates(): (Date | null)[] {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const result: (Date | null)[] = [];
  for (let i = 0; i < firstDay.getDay(); i++) result.push(null);
  for (let d = 1; d <= lastDay.getDate(); d++) result.push(new Date(year, month, d));
  while (result.length % 7 !== 0) result.push(null);
  return result;
}

function groupByDate(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const map = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = event.start.split('T')[0];
    const arr = map.get(key) ?? [];
    arr.push(event);
    map.set(key, arr);
  }
  return map;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

// ── Daily View ───────────────────────────────────────────────────────────────

function DailyView({ events }: { events: CalendarEvent[] }) {
  const today = new Date();
  const todayKey = toDateKey(today);
  const todayEvents = events
    .filter(e => e.start.startsWith(todayKey))
    .sort((a, b) => a.start.localeCompare(b.start));
  const allDay = todayEvents.filter(e => e.all_day);
  const timed = todayEvents.filter(e => !e.all_day);
  const dayLabel = today.toLocaleDateString([], {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });

  return (
    <div className={styles.dailyContainer}>
      <div className={styles.dailyDate}>{dayLabel}</div>
      {allDay.length > 0 && (
        <div className={styles.dailySection}>
          <div className={styles.dailySectionLabel}>All Day</div>
          {allDay.map(e => (
            <div key={e.id} className={styles.dailyEvent}>
              <span className={styles.dailyEventTitle}>{e.title}</span>
            </div>
          ))}
        </div>
      )}
      {timed.length > 0 ? (
        <div className={styles.dailySection}>
          {timed.map(e => (
            <div key={e.id} className={styles.dailyEvent}>
              <span className={styles.dailyEventTime}>{formatTime(e.start)}</span>
              <span className={styles.dailyEventTitle}>{e.title}</span>
            </div>
          ))}
        </div>
      ) : allDay.length === 0 ? (
        <div className={styles.emptyState}>Nothing scheduled today</div>
      ) : null}
    </div>
  );
}

// ── Weekly View ──────────────────────────────────────────────────────────────

function WeeklyView({ events }: { events: CalendarEvent[] }) {
  const weekDates = getWeekDates();
  const byDate = groupByDate(events);
  const MAX_SHOWN = 5;

  return (
    <div className={styles.weekGrid}>
      {weekDates.map((date, i) => {
        const key = toDateKey(date);
        const dayEvents = (byDate.get(key) ?? []).sort((a, b) => a.start.localeCompare(b.start));
        const today = isToday(date);
        const shown = dayEvents.slice(0, MAX_SHOWN);
        const overflow = dayEvents.length - MAX_SHOWN;

        return (
          <div key={key} className={`${styles.weekDay} ${today ? styles.weekDayToday : ''}`}>
            <div className={styles.weekDayHeader}>
              <span className={styles.weekDayName}>{DAY_NAMES_SHORT[i]}</span>
              <span className={`${styles.weekDayNum} ${today ? styles.weekDayNumToday : ''}`}>
                {date.getDate()}
              </span>
            </div>
            <div className={styles.weekDayEvents}>
              {shown.map(e => (
                <div key={e.id} className={styles.weekEvent}>
                  {!e.all_day && (
                    <span className={styles.weekEventTime}>{formatTime(e.start)}</span>
                  )}
                  <span className={styles.weekEventTitle}>{e.title}</span>
                </div>
              ))}
              {overflow > 0 && (
                <div className={styles.weekEventOverflow}>+{overflow} more</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Monthly View ─────────────────────────────────────────────────────────────

function MonthlyView({ events }: { events: CalendarEvent[] }) {
  const today = new Date();
  const monthDates = getMonthDates();
  const byDate = groupByDate(events);
  const numWeeks = monthDates.length / 7;
  const monthLabel = today.toLocaleDateString([], { month: 'long', year: 'numeric' });
  const MAX_SHOWN = 3;

  return (
    <div className={styles.monthContainer}>
      <div className={styles.monthLabel}>{monthLabel}</div>
      <div
        className={styles.monthGrid}
        style={{ gridTemplateRows: `auto repeat(${numWeeks}, 1fr)` }}
      >
        {DAY_NAMES_HEADER.map((d, i) => (
          <div key={i} className={styles.monthDayHeader}>{d}</div>
        ))}
        {monthDates.map((date, i) => {
          if (!date) {
            return <div key={`pad-${i}`} className={styles.monthCellEmpty} />;
          }
          const key = toDateKey(date);
          const dayEvents = (byDate.get(key) ?? []).sort((a, b) => a.start.localeCompare(b.start));
          const today_ = isToday(date);
          const shown = dayEvents.slice(0, MAX_SHOWN);
          const overflow = dayEvents.length - MAX_SHOWN;

          return (
            <div key={key} className={`${styles.monthCell} ${today_ ? styles.monthCellToday : ''}`}>
              <span className={`${styles.monthDateNum} ${today_ ? styles.monthDateNumToday : ''}`}>
                {date.getDate()}
              </span>
              <div className={styles.monthEvents}>
                {shown.map(e => (
                  <div key={e.id} className={styles.monthEvent} title={e.title}>
                    {e.title}
                  </div>
                ))}
                {overflow > 0 && (
                  <div className={styles.monthEventOverflow}>+{overflow}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Calendar View (root) ─────────────────────────────────────────────────────

export default function CalendarView() {
  const [view, setView] = useState<CalView>('weekly');
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );
  const { events, loading } = useCalendarData();

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const VIEWS: CalView[] = ['daily', 'weekly', 'monthly'];

  return (
    <div className={`${styles.container} view-enter`}>
      <div className={styles.header}>
        <span className={styles.viewLabel}>Calendar</span>
        <div className={styles.toggle}>
          {VIEWS.map(v => (
            <button
              key={v}
              className={`${styles.toggleBtn} ${view === v ? styles.toggleBtnActive : ''}`}
              onClick={() => setView(v)}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        <span className={styles.clock}>{time}</span>
      </div>

      <div className={styles.calendarBody}>
        {loading ? (
          <div className={styles.emptyState}>Loading…</div>
        ) : (
          <>
            {view === 'daily' && <DailyView events={events} />}
            {view === 'weekly' && <WeeklyView events={events} />}
            {view === 'monthly' && <MonthlyView events={events} />}
          </>
        )}
      </div>
    </div>
  );
}
