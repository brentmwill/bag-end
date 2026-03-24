import { useState, useEffect } from 'react';
import { GlanceData, TrelloTask, BabyMealSlot, FreezerItem } from '../types';
import styles from './HouseholdView.module.css';

interface Props {
  data: GlanceData | null;
}

const BABY_SLOT_ORDER = [
  'breakfast',
  'morning_snack',
  'lunch',
  'afternoon_snack',
  'dinner',
];

const BABY_SLOT_LABELS: Record<string, string> = {
  breakfast: 'Breakfast',
  morning_snack: 'AM Snack',
  lunch: 'Lunch',
  afternoon_snack: 'PM Snack',
  dinner: 'Dinner',
};

function formatDue(dueStr: string): string {
  const d = new Date(dueStr);
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function isOverdue(dueStr: string): boolean {
  return new Date(dueStr) < new Date();
}

function formatFrozenDate(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

interface TrelloGroup {
  list_name: string;
  tasks: TrelloTask[];
}

function groupByList(tasks: TrelloTask[]): TrelloGroup[] {
  const map = new Map<string, TrelloTask[]>();
  for (const task of tasks) {
    const arr = map.get(task.list_name) ?? [];
    arr.push(task);
    map.set(task.list_name, arr);
  }
  return Array.from(map.entries()).map(([list_name, ts]) => ({ list_name, tasks: ts }));
}

export default function HouseholdView({ data }: Props) {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const household = data?.household ?? null;
  const tasks: TrelloTask[] = household?.trello_tasks ?? [];
  const babySlots: BabyMealSlot[] = household?.baby_meal_slots ?? [];
  const freezerItems: FreezerItem[] = household?.freezer_items ?? [];

  const trelloGroups = groupByList(tasks);

  // Build ordered slot map
  const slotMap = new Map<string, BabyMealSlot>();
  for (const slot of babySlots) {
    slotMap.set(slot.slot_type, slot);
  }

  return (
    <div className={`${styles.container} view-enter`}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.viewLabel}>Household</span>
        <span className={styles.clock}>{time}</span>
      </div>

      {/* Trello Tasks */}
      <div className={styles.card}>
        <div className={styles.cardLabel}>Tasks</div>
        {trelloGroups.length > 0 ? (
          <div className={styles.trelloGroups}>
            {trelloGroups.map(group => (
              <div key={group.list_name} className={styles.trelloGroup}>
                <div className={styles.trelloGroupHeader}>{group.list_name}</div>
                {group.tasks.map(task => (
                  <div key={task.id} className={styles.trelloTask}>
                    <div className={`${styles.taskCheckbox} ${task.completed ? styles.taskCheckboxDone : ''}`}>
                      {task.completed && <span className={styles.taskCheckIcon}>✓</span>}
                    </div>
                    <div className={styles.taskContent}>
                      <div className={`${styles.taskName} ${task.completed ? styles.taskNameDone : ''}`}>
                        {task.name}
                      </div>
                      {task.due && (
                        <div className={`${styles.taskDue} ${!task.completed && isOverdue(task.due) ? styles.taskDueOverdue : ''}`}>
                          Due {formatDue(task.due)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>All clear ✓</div>
        )}
      </div>

      {/* Baby Meal Slots */}
      <div className={styles.card}>
        <div className={styles.cardLabel}>Baby Meals Today</div>
        <div className={styles.mealSlotsGrid}>
          {BABY_SLOT_ORDER.map(slotType => {
            const slot = slotMap.get(slotType);
            const logged = slot?.logged ?? false;
            return (
              <div key={slotType} className={styles.mealSlot}>
                <span
                  className={`${styles.mealSlotIndicator} ${
                    logged ? styles.mealSlotIndicatorLogged : styles.mealSlotIndicatorEmpty
                  }`}
                >
                  {logged ? '●' : '○'}
                </span>
                <span className={styles.mealSlotLabel}>
                  {BABY_SLOT_LABELS[slotType] ?? slotType}
                </span>
                {slot?.description && (
                  <span className={styles.mealSlotDescription} title={slot.description}>
                    {slot.description}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Freezer Inventory */}
      <div className={styles.card}>
        <div className={styles.cardLabel}>Freezer</div>
        {freezerItems.length > 0 ? (
          <div className={styles.freezerList}>
            {freezerItems.map(item => (
              <div key={item.id} className={styles.freezerItem}>
                <span className={styles.freezerName}>{item.recipe_name}</span>
                <span className={styles.freezerServings}>{item.servings} srv</span>
                <span className={styles.freezerDate}>{formatFrozenDate(item.date_frozen)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState} style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
            Freezer is empty
          </div>
        )}
      </div>
    </div>
  );
}
