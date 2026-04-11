import { useState, useEffect, useCallback } from 'react';
import { Recipe, MealPlanSlot } from '../types';

export interface WeekDay {
  date: string;       // YYYY-MM-DD
  label: string;      // "Mon 3/31"
  isWeekday: boolean;
  slot: MealPlanSlot | null;
  babyLunchSlot: MealPlanSlot | null;
  babySnackSlots: MealPlanSlot[];
  babyLunchSuggestion: string | null;
}

export interface Filters {
  categories: string[];
  pregnancy_safe: boolean;
  baby_friendly: boolean;
  freezable: boolean;
  finger_food: boolean;
}

function getSundayOfWeek(d: Date): Date {
  const sunday = new Date(d);
  sunday.setDate(d.getDate() - d.getDay()); // getDay: Sun=0, so this always lands on Sunday
  sunday.setHours(0, 0, 0, 0);
  return sunday;
}

function toDateStr(d: Date): string {
  return d.toISOString().split('T')[0];
}

function buildWeekDays(sunday: Date): WeekDay[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(sunday);
    d.setDate(sunday.getDate() + i);
    return {
      date: toDateStr(d),
      label: d.toLocaleDateString([], { weekday: 'short', month: 'numeric', day: 'numeric' }),
      isWeekday: d.getDay() >= 1 && d.getDay() <= 5,
      slot: null,
      babyLunchSlot: null,
      babySnackSlots: [],
      babyLunchSuggestion: null,
    };
  });
}

export function useMealPlanner() {
  const sunday = getSundayOfWeek(new Date());
  const weekStart = toDateStr(sunday);
  const weekEnd = toDateStr(new Date(sunday.getTime() + 6 * 86400000));

  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [weekDays, setWeekDays] = useState<WeekDay[]>(buildWeekDays(sunday));
  const [filters, setFilters] = useState<Filters>({
    categories: [],
    pregnancy_safe: false,
    baby_friendly: false,
    freezable: false,
    finger_food: false,
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
    if (filters.finger_food) params.append('category', 'Finger Food');

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
          babyLunchSlot: slots.find(s => s.date === day.date && s.meal_type === 'baby_lunch') ?? null,
          babySnackSlots: slots.filter(s => s.date === day.date && s.meal_type === 'baby_snack'),
        })));
      })
      .catch(console.error);
  }, [weekStart, weekEnd]);

  useEffect(() => { fetchWeekSlots(); }, [fetchWeekSlots]);

  // Fetch baby lunch suggestions for weekdays
  useEffect(() => {
    const weekdayDates = buildWeekDays(sunday)
      .filter(d => d.isWeekday)
      .map(d => d.date);

    Promise.all(
      weekdayDates.map(dateStr =>
        fetch(`/api/meal-plan/suggest-baby-lunch?date=${dateStr}`)
          .then(r => r.json())
          .then((data: { suggestion: string | null }) => ({ date: dateStr, suggestion: data.suggestion }))
          .catch(() => ({ date: dateStr, suggestion: null }))
      )
    ).then(results => {
      const suggestionMap = new Map(results.map(r => [r.date, r.suggestion]));
      setWeekDays(prev => prev.map(day => ({
        ...day,
        babyLunchSuggestion: suggestionMap.get(day.date) ?? null,
      })));
    });
  }, [weekStart]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const saveBabySlot = useCallback(async (date: string, meal_type: 'baby_lunch' | 'baby_snack', notes: string, existingId?: string) => {
    if (existingId) {
      await fetch(`/api/meal-plan/${existingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes }),
      });
    } else {
      await fetch('/api/meal-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, meal_type, notes, source: 'planned' }),
      });
    }
    fetchWeekSlots();
  }, [fetchWeekSlots]);

  const removeBabySlot = useCallback(async (slotId: string) => {
    await fetch(`/api/meal-plan/${slotId}`, { method: 'DELETE' });
    fetchWeekSlots();
  }, [fetchWeekSlots]);

  const updateRecipeCategories = useCallback(async (recipeId: string, categories: string[]) => {
    await fetch(`/api/recipes/${recipeId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ categories }),
    });
    // Refresh recipe list
    const params = new URLSearchParams();
    filters.categories.forEach(c => params.append('category', c));
    if (filters.pregnancy_safe) params.set('pregnancy_safe', 'true');
    if (filters.baby_friendly) params.set('baby_friendly', 'true');
    if (filters.freezable) params.set('freezable', 'true');
    if (filters.finger_food) params.append('category', 'Finger Food');
    const res = await fetch(`/api/recipes?${params}`);
    setRecipes(await res.json());
  }, [filters]);

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
    saveBabySlot,
    removeBabySlot,
    updateRecipeCategories,
    pushToAnyList,
    toggleCategory,
    toggleBoolean,
  };
}
