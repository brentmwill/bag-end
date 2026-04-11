export interface WeatherCurrent {
  temp: number;
  weathercode: number;
  windspeed: number;
}

export interface WeatherDay {
  date: string;
  max: number;
  min: number;
  precip_prob: number;
  code: number;
}

export interface WeatherData {
  current: WeatherCurrent;
  forecast: WeatherDay[];
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: string; // ISO datetime
  end: string;
  all_day: boolean;
  calendar_id: string;
}

export interface CommuteTile {
  label: string; // e.g. "Brent → Work"
  duration_min: number;
  distance_km: number;
}

export interface TrelloTask {
  id: string;
  name: string;
  list_name: string;
  due: string | null;
  completed: boolean;
}

export interface BabyMealSlot {
  slot_type: string;
  description: string | null;
  logged: boolean;
}

export interface FreezerItem {
  id: string;
  recipe_name: string;
  servings: number;
  date_frozen: string;
}

export interface MealPlanDay {
  date: string;
  dinner: string | null;
  baby_lunch?: string | null;
  baby_snacks?: string[];
}

export interface WordOfDay {
  word: string;
  pronunciation: string | null;
  definition: string;
  etymology: string | null;
  example: string | null;
}

export interface HomeView {
  weather: WeatherData | null;
  tonight_meal: string | null;
  calendar_events: CalendarEvent[];
  commute_tiles: CommuteTile[];
  digest_snippet: string | null;
}

export interface PlanningView {
  meal_plan_week: MealPlanDay[];
  calendar_week: CalendarEvent[];
}

export interface SportsGame {
  opponent: string;
  opponent_name: string;
  home: boolean;
  completed: boolean;
  date: string | null;
  time: string | null;
  score?: string;
  won?: boolean;
}

export interface SportsTeam {
  id: string;
  label: string;
  last_game: SportsGame | null;
  next_game: SportsGame | null;
}

export interface HouseholdView {
  trello_tasks: TrelloTask[];
  baby_meal_slots: BabyMealSlot[];
  freezer_items: FreezerItem[];
  sports_teams: SportsTeam[];
}

export interface AmbientView {
  word_of_day: WordOfDay | null;
}

export interface Recipe {
  id: string;
  name: string;
  categories: string[];
  tags: string[];
  rating: number | null;
  prep_time: string | null;
  cook_time: string | null;
  servings: string | null;
  photo_path: string | null;
  pregnancy_safe: boolean;
  baby_friendly: boolean;
  freezable: boolean;
  batch_cookable: boolean;
}

export interface MealPlanSlot {
  id: string;
  date: string;
  meal_type: string;
  recipe_id: string | null;
  recipe_name: string | null;
  recipe_photo: string | null;
  notes: string | null;
  source: string;
}

export interface GeneratedRecipe {
  name: string;
  prep_time: string | null;
  cook_time: string | null;
  servings: string | null;
  ingredients: Array<{ quantity: string | null; display_text: string }>;
  directions: string[];
  notes: string | null;
  id?: string;
  saved: boolean;
}

export interface GlanceData {
  home: HomeView | null;
  planning: PlanningView | null;
  household: HouseholdView | null;
  ambient: AmbientView | null;
  cached_at: string | null;
}
