import { useState, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  PointerSensor,
  TouchSensor,
} from '@dnd-kit/core';
import { useMealPlanner, WeekDay } from '../hooks/useMealPlanner';
import { Recipe } from '../types';
import GenerateRecipeModal from '../components/GenerateRecipeModal';
import styles from './MealPlannerOverlay.module.css';

const CATEGORY_GROUPS = [
  { label: 'Diet', cats: ['Mediterranean', 'Green Mediterranean', 'Anti-Inflammatory', 'High Protein'] },
  { label: 'Type', cats: ['Breakfast', 'Dinner', 'Snack', 'Pasta', 'Soups and Stews', 'Casserole'] },
  { label: 'Method', cats: ['Slow Cooker Recipes'] },
];

// --- Draggable Recipe Card ---

interface RecipeCardProps {
  recipe: Recipe;
  isDragging?: boolean;
  onCategoryEdit?: (recipe: Recipe) => void;
}

function RecipeCard({ recipe, isDragging, onCategoryEdit }: RecipeCardProps) {
  const stars = recipe.rating ? '★'.repeat(recipe.rating) : null;
  return (
    <div className={`${styles.recipeCard} ${isDragging ? styles.recipeCardDragging : ''}`}>
      <div className={styles.recipeCardBody}>
        <div className={styles.recipeNameRow}>
          <div className={styles.recipeName}>{recipe.name}</div>
          {onCategoryEdit && (
            <button
              className={styles.editTagsBtn}
              onClick={e => { e.stopPropagation(); onCategoryEdit(recipe); }}
              title="Edit tags"
            >
              ✎
            </button>
          )}
        </div>
        <div className={styles.recipeMeta}>
          {recipe.cook_time && <span>{recipe.cook_time}</span>}
          {stars && <span className={styles.stars}>{stars}</span>}
        </div>
        {recipe.categories.length > 0 && (
          <div className={styles.recipeTags}>
            {recipe.categories.slice(0, 2).map(c => (
              <span key={c} className={styles.categoryTag}>{c}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DraggableRecipeCard({ recipe, onCategoryEdit }: { recipe: Recipe; onCategoryEdit: (r: Recipe) => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: recipe.id, data: { recipe } });
  return (
    <div ref={setNodeRef} {...listeners} {...attributes} style={{ opacity: isDragging ? 0.4 : 1 }}>
      <RecipeCard recipe={recipe} isDragging={isDragging} onCategoryEdit={onCategoryEdit} />
    </div>
  );
}

// --- Baby text input with save-on-blur ---

interface BabyInputProps {
  placeholder: string;
  initialValue: string;
  suggestion?: string | null;
  onSave: (value: string) => void;
  onClear?: () => void;
}

function BabyInput({ placeholder, initialValue, suggestion, onSave, onClear }: BabyInputProps) {
  const [value, setValue] = useState(initialValue);
  const isDirty = useRef(false);

  useEffect(() => {
    setValue(initialValue);
    isDirty.current = false;
  }, [initialValue]);

  const handleBlur = () => {
    if (isDirty.current) {
      if (value.trim()) {
        onSave(value.trim());
      } else if (onClear) {
        onClear();
      }
      isDirty.current = false;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
  };

  return (
    <div className={styles.babyInputRow}>
      <input
        className={styles.babyInput}
        value={value}
        placeholder={suggestion ? `e.g. ${suggestion}` : placeholder}
        onChange={e => { setValue(e.target.value); isDirty.current = true; }}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
      />
      {value && onClear && (
        <button className={styles.babyInputClear} onClick={() => { setValue(''); if (onClear) onClear(); }}>✕</button>
      )}
    </div>
  );
}

// --- Droppable Day Slot ---

interface DaySlotProps {
  day: WeekDay;
  onRemove: (slotId: string) => void;
  onSaveBaby: (date: string, type: 'baby_lunch' | 'baby_snack', notes: string, existingId?: string) => void;
  onRemoveBaby: (slotId: string) => void;
}

function DaySlot({ day, onRemove, onSaveBaby, onRemoveBaby }: DaySlotProps) {
  const { setNodeRef, isOver } = useDroppable({ id: day.date });
  const snack1 = day.babySnackSlots[0] ?? null;
  const snack2 = day.babySnackSlots[1] ?? null;

  return (
    <div className={styles.daySlotWrapper}>
      {/* Dinner drop zone */}
      <div
        ref={setNodeRef}
        className={`${styles.daySlot} ${isOver ? styles.daySlotOver : ''}`}
      >
        <div className={styles.dayLabel}>{day.label}</div>
        {day.slot?.recipe_name ? (
          <div className={styles.slotFilled}>
            <span className={styles.slotRecipeName}>{day.slot.recipe_name}</span>
            <button
              className={styles.removeBtn}
              onClick={() => day.slot && onRemove(day.slot.id)}
            >
              ✕
            </button>
          </div>
        ) : (
          <div className={styles.slotEmpty}>Drop dinner here</div>
        )}
      </div>

      {/* Baby slots — weekdays only */}
      {day.isWeekday && (
        <div className={styles.babySlots}>
          <div className={styles.babySlotsLabel}>Baby</div>
          <BabyInput
            placeholder="Lunch"
            initialValue={day.babyLunchSlot?.notes ?? ''}
            suggestion={day.babyLunchSuggestion}
            onSave={notes => onSaveBaby(day.date, 'baby_lunch', notes, day.babyLunchSlot?.id)}
            onClear={day.babyLunchSlot ? () => onRemoveBaby(day.babyLunchSlot!.id) : undefined}
          />
          <BabyInput
            placeholder="Snack 1"
            initialValue={snack1?.notes ?? ''}
            onSave={notes => onSaveBaby(day.date, 'baby_snack', notes, snack1?.id)}
            onClear={snack1 ? () => onRemoveBaby(snack1.id) : undefined}
          />
          <BabyInput
            placeholder="Snack 2"
            initialValue={snack2?.notes ?? ''}
            onSave={notes => onSaveBaby(day.date, 'baby_snack', notes, snack2?.id)}
            onClear={snack2 ? () => onRemoveBaby(snack2.id) : undefined}
          />
        </div>
      )}
    </div>
  );
}

// --- Category edit modal ---

interface CategoryEditModalProps {
  recipe: Recipe;
  onSave: (categories: string[]) => void;
  onClose: () => void;
}

const ALL_EDITABLE_CATEGORIES = [
  'Mediterranean', 'Green Mediterranean', 'Anti-Inflammatory', 'High Protein',
  'Breakfast', 'Dinner', 'Snack', 'Pasta', 'Soups and Stews', 'Casserole',
  'Slow Cooker Recipes', 'Finger Food',
];

function CategoryEditModal({ recipe, onSave, onClose }: CategoryEditModalProps) {
  const [selected, setSelected] = useState<string[]>(recipe.categories);

  const toggle = (cat: string) => {
    setSelected(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    );
  };

  return (
    <div className={styles.categoryModalBackdrop} onClick={onClose}>
      <div className={styles.categoryModal} onClick={e => e.stopPropagation()}>
        <div className={styles.categoryModalTitle}>{recipe.name}</div>
        <div className={styles.categoryModalTags}>
          {ALL_EDITABLE_CATEGORIES.map(cat => (
            <button
              key={cat}
              className={`${styles.filterChip} ${selected.includes(cat) ? styles.filterChipActive : ''}`}
              onClick={() => toggle(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className={styles.categoryModalActions}>
          <button className={styles.categoryModalSave} onClick={() => { onSave(selected); onClose(); }}>Save</button>
          <button className={styles.categoryModalCancel} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

// --- Main Overlay ---

interface Props {
  onClose: () => void;
}

export default function MealPlannerOverlay({ onClose }: Props) {
  const {
    recipes,
    weekDays,
    filters,
    loadingRecipes,
    pushStatus,
    assignRecipe,
    removeRecipe,
    saveBabySlot,
    removeBabySlot,
    updateRecipeCategories,
    pushToAnyList,
    toggleCategory,
    toggleBoolean,
    setSearch,
  } = useMealPlanner();

  const [activeRecipe, setActiveRecipe] = useState<Recipe | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [editingRecipe, setEditingRecipe] = useState<Recipe | null>(null);

  // Default dnd-kit sensors don't recognize touch on mobile. Add explicit
  // PointerSensor for mouse and TouchSensor with a press-hold delay so a
  // touch-and-drag is distinguishable from a scroll.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } }),
  );

  const handleDragStart = (event: any) => {
    setActiveRecipe(event.active.data.current?.recipe ?? null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveRecipe(null);
    const { active, over } = event;
    if (!over) return;
    const recipe: Recipe = active.data.current?.recipe;
    const date: string = over.id as string;
    if (recipe && date) {
      assignRecipe(date, recipe);
    }
  };

  const pushLabel = {
    idle: 'Push to Grocery List',
    pushing: 'Pushing…',
    done: '✓ Added to AnyList',
    error: 'Push Failed',
  }[pushStatus];

  const overlay = (
    <div className={styles.overlay}>
      <div className={styles.header}>
        <span className={styles.title}>Meal Planner</span>
        <div className={styles.headerActions}>
          <button className={styles.generateBtn} onClick={() => setShowGenerate(true)}>
            Generate Recipe
          </button>
          <button
            className={`${styles.pushBtn} ${pushStatus !== 'idle' ? styles.pushBtnActive : ''}`}
            onClick={pushToAnyList}
            disabled={pushStatus === 'pushing'}
          >
            {pushLabel}
          </button>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>
      </div>

      {/* Search */}
      <div className={styles.searchRow}>
        <input
          className={styles.searchInput}
          type="search"
          placeholder="Search recipes…"
          value={filters.search}
          onChange={e => setSearch(e.target.value)}
          autoComplete="off"
        />
        {filters.search && (
          <button
            className={styles.searchClear}
            onClick={() => setSearch('')}
            aria-label="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        {CATEGORY_GROUPS.map(group => (
          <div key={group.label} className={styles.filterGroup}>
            <span className={styles.filterGroupLabel}>{group.label}</span>
            {group.cats.map(cat => (
              <button
                key={cat}
                className={`${styles.filterChip} ${filters.categories.includes(cat) ? styles.filterChipActive : ''}`}
                onClick={() => toggleCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        ))}
        <div className={styles.filterGroup}>
          <span className={styles.filterGroupLabel}>Family</span>
          <button
            className={`${styles.filterChip} ${filters.baby_friendly ? styles.filterChipActive : ''}`}
            onClick={() => toggleBoolean('baby_friendly')}
          >
            Baby-friendly
          </button>
          <button
            className={`${styles.filterChip} ${filters.finger_food ? styles.filterChipActive : ''}`}
            onClick={() => toggleBoolean('finger_food')}
          >
            Finger Food
          </button>
          <button
            className={`${styles.filterChip} ${filters.pregnancy_safe ? styles.filterChipActive : ''}`}
            onClick={() => toggleBoolean('pregnancy_safe')}
          >
            Pregnancy-safe
          </button>
          <button
            className={`${styles.filterChip} ${filters.freezable ? styles.filterChipActive : ''}`}
            onClick={() => toggleBoolean('freezable')}
          >
            Freezable
          </button>
        </div>
      </div>

      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className={styles.body}>
          {/* Recipe list */}
          <div className={styles.recipePanel}>
            {loadingRecipes ? (
              <div className={`${styles.emptyState} pulse`}>Loading…</div>
            ) : recipes.length === 0 ? (
              <div className={styles.emptyState}>No recipes match these filters.</div>
            ) : (
              <div className={styles.recipeGrid}>
                {recipes.map(r => (
                  <DraggableRecipeCard
                    key={r.id}
                    recipe={r}
                    onCategoryEdit={setEditingRecipe}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Week schedule */}
          <div className={styles.weekPanel}>
            <div className={styles.weekTitle}>This Week</div>
            {weekDays.map(day => (
              <DaySlot
                key={day.date}
                day={day}
                onRemove={removeRecipe}
                onSaveBaby={saveBabySlot}
                onRemoveBaby={removeBabySlot}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeRecipe ? <RecipeCard recipe={activeRecipe} isDragging /> : null}
        </DragOverlay>
      </DndContext>

      {showGenerate && (
        <GenerateRecipeModal
          filters={filters}
          onSaved={() => setShowGenerate(false)}
          onClose={() => setShowGenerate(false)}
        />
      )}

      {editingRecipe && (
        <CategoryEditModal
          recipe={editingRecipe}
          onSave={cats => updateRecipeCategories(editingRecipe.id, cats)}
          onClose={() => setEditingRecipe(null)}
        />
      )}
    </div>
  );

  return ReactDOM.createPortal(overlay, document.body);
}
