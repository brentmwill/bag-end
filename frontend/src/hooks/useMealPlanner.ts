import { useState, useEffect, useCallback } from 'react';
import { Recipe, MealPlanSlot } from '../types';

export interface WeekDay {
  date: string;       // YYYY-MM-DD
  label: string;      // "Mon 3/31"
  slot: MealPlanSlot | null;
}

export interface Filters {
  categories: string[];
  pregnancy_safe: boolean;
  baby_friendly: boolean;
  freezable: boolean;
}

function getMondayOfWeek(d: Date): Date {
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diff);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function toDateStr(d: Date): string {
  return d.toISOString().split('T')[0];
}

function buildWeekDays(monday: Date): WeekDay[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return {
      date: toDateStr(d),
      label: d.toLocaleDateString([], { weekday: 'short', month: 'numeric', day: 'numeric' }),
      slot: null,
    };
  });
}

export function useMealPlanner() {
  const monday = getMondayOfWeek(new Date());
  const weekStart = toDateStr(monday);
  const weekEnd = toDateStr(new Date(monday.getTime() + 6 * 86400000));

  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [weekDays, setWeekDays] = useState<WeekDay[]>(buildWeekDays(monday));
  const [filters, setFilters] = useState<Filters>({
    categories: [],
    pregnancy_safe: false,
    baby_friendly: false,
    freezable: false,
  });
  const [loadingRecipes, setLoadingRecipes] = useState(false);
  const [pushStatus, setPushStatus] = useState<'idle' | 'pushing' | 'done' | 'error'>('idle');

  // Fetch recipes when filters change
  useEffect(() => {
    setLoadingRecipes(true);
    const params = new URLSearchParams();
    filters.categories.forEach(c => params.append('category', c));
    if (filters.pregnancy_safe) params.set('pregnancy_safe', 'true');
    if (filters.baby_friendly) params.set('baby_friendly', 'true');
    if (filters.freezable) params.set('freezable', 'true');

    fetch(`/api/recipes?${params}`)
      .then(r => r.json())
      .then(setRecipes)
      .catch(console.error)
      .finally(() => setLoadingRecipes(false));
  }, [filters]);

  // Fetch current week slots
  const fetchWeekSlots = useCallback(() => {
    fetch(`/api/meal-plan?start=${weekStart}&end=${weekEnd}`)
      .then(r => r.json())
      .then((slots: MealPlanSlot[]) => {
        setWeekDays(prev => prev.map(day => ({
          ...day,
          slot: slots.find(s => s.date === day.date && s.meal_type === 'dinner') ?? null,
        })));
      })
      .catch(console.error);
  }, [weekStart, weekEnd]);

  useEffect(() => { fetchWeekSlots(); }, [fetchWeekSlots]);

  const assignRecipe = useCallback(async (date: string, recipe: Recipe) => {
    const existing = weekDays.find(d => d.date === date)?.slot;
    if (existing) {
      await fetch(`/api/meal-plan/${existing.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipe_id: recipe.id }),
      });
    } else {
      await fetch('/api/meal-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, meal_type: 'dinner', recipe_id: recipe.id, source: 'planned' }),
      });
    }
    fetchWeekSlots();
  }, [weekDays, fetchWeekSlots]);

  const removeRecipe = useCallback(async (slotId: string) => {
    await fetch(`/api/meal-plan/${slotId}`, { method: 'DELETE' });
    fetchWeekSlots();
  }, [fetchWeekSlots]);

  const pushToAnyList = useCallback(async () => {
    setPushStatus('pushing');
    try {
      const res = await fetch('/api/meal-plan/push-to-anylist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ week_start: weekStart }),
      });
      if (!res.ok) throw new Error(await res.text());
      setPushStatus('done');
      setTimeout(() => setPushStatus('idle'), 3000);
    } catch {
      setPushStatus('error');
      setTimeout(() => setPushStatus('idle'), 3000);
    }
  }, [weekStart]);

  const toggleCategory = useCallback((cat: string) => {
    setFilters(f => ({
      ...f,
      categories: f.categories.includes(cat)
        ? f.categories.filter(c => c !== cat)
        : [...f.categories, cat],
    }));
  }, []);

  const toggleBoolean = useCallback((key: keyof Omit<Filters, 'categories'>) => {
    setFilters(f => ({ ...f, [key]: !f[key] }));
  }, []);

  return {
    recipes,
    weekDays,
    filters,
    loadingRecipes,
    pushStatus,
    weekStart,
    assignRecipe,
    removeRecipe,
    pushToAnyList,
    toggleCategory,
    toggleBoolean,
  };
}
