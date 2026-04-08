import { useState, useEffect } from 'react';
import { GlanceData, CalendarEvent, MealPlanDay } from '../types';
import MealPlannerOverlay from './MealPlannerOverlay';
import styles from './PlanningView.module.css';

interface Props {
  data: GlanceData | null;
}

function formatDayShort(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString([], { weekday: 'short' });
}

function formatDayFull(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
}

function isToday(dateStr: string): boolean {
  const today = new Date();
  const d = new Date(dateStr + 'T12:00:00');
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  );
}

function formatEventTime(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function getEventDateStr(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toISOString().split('T')[0];
}

function isTodayDate(isoStr: string): boolean {
  const today = new Date();
  const d = new Date(isoStr);
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  );
}

interface DayGroup {
  dateStr: string;
  label: string;
  events: CalendarEvent[];
}

function groupEventsByDay(events: CalendarEvent[]): DayGroup[] {
  const map = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const key = getEventDateStr(event.start);
    const arr = map.get(key) ?? [];
    arr.push(event);
    map.set(key, arr);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([dateStr, evts]) => ({
      dateStr,
      label: formatDayFull(dateStr),
      events: evts.sort((a, b) => a.start.localeCompare(b.start)),
    }));
}

export default function PlanningView({ data }: Props) {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const [plannerOpen, setPlannerOpen] = useState(false);
  const planning = data?.planning ?? null;
  const mealPlan: MealPlanDay[] = planning?.meal_plan_week ?? [];
  const calendarWeek: CalendarEvent[] = planning?.calendar_week ?? [];
  const dayGroups = groupEventsByDay(calendarWeek);

  return (
    <div className={`${styles.container} view-enter`}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.viewLabel}>Planning</span>
        <button className={styles.planMealsBtn} onClick={() => setPlannerOpen(true)}>
          Plan Meals
        </button>
        <span className={styles.clock}>{time}</span>
      </div>

      {plannerOpen && <MealPlannerOverlay onClose={() => setPlannerOpen(false)} />}

      {/* Week Meal Plan */}
      <div className={styles.sectionCard}>
        <div className={styles.sectionLabel}>Meal Plan — This Week</div>
        {mealPlan.length > 0 ? (
          <div className={styles.mealPlanList}>
            {mealPlan.map(day => {
              const today = isToday(day.date);
              return (
                <div
                  key={day.date}
                  className={`${styles.mealPlanRow} ${today ? styles.mealPlanRowToday : ''}`}
                >
                  <span className={`${styles.mealPlanDay} ${today ? styles.mealPlanDayToday : ''}`}>
                    {formatDayShort(day.date)}
                  </span>
                  <div className={styles.mealPlanMeals}>
                    {day.dinner ? (
                      <span className={styles.mealPlanDinner}>{day.dinner}</span>
                    ) : (
                      <span className={styles.mealPlanEmpty}>—</span>
                    )}
                    {(day.baby_lunch || (day.baby_snacks && day.baby_snacks.length > 0)) && (
                      <div className={styles.mealPlanBaby}>
                        {day.baby_lunch && (
                          <span className={styles.mealPlanBabyItem}>🍼 {day.baby_lunch}</span>
                        )}
                        {day.baby_snacks?.map((snack, i) => (
                          <span key={i} className={styles.mealPlanBabyItem}>· {snack}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className={styles.emptyState}>No meal plan for this week</div>
        )}
      </div>

      {/* Calendar Week */}
      <div className={styles.sectionCard}>
        <div className={styles.sectionLabel}>Events — This Week</div>
        {dayGroups.length > 0 ? (
          <div className={styles.calendarWeek}>
            {dayGroups.map(group => (
              <div key={group.dateStr} className={styles.dayGroup}>
                <div
                  className={`${styles.dayHeader} ${
                    isTodayDate(group.dateStr + 'T12:00:00') ? styles.dayHeaderToday : ''
                  }`}
                >
                  {group.label}
                </div>
                {group.events.map(event => (
                  <div key={event.id} className={styles.calendarEvent}>
                    <span className={styles.eventTime}>
                      {event.all_day ? 'All day' : formatEventTime(event.start)}
                    </span>
                    <span className={styles.eventTitle}>{event.title}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>No events this week</div>
        )}
      </div>
    </div>
  );
}
