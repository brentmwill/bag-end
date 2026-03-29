import { useState } from 'react';
import ReactDOM from 'react-dom';
import { DndContext, DragEndEvent, DragOverlay, useDraggable, useDroppable } from '@dnd-kit/core';
import { useMealPlanner, WeekDay } from '../hooks/useMealPlanner';
import { Recipe } from '../types';
import GenerateRecipeModal from '../components/GenerateRecipeModal';
import styles from './MealPlannerOverlay.module.css';

const CATEGORY_GROUPS = [
  { label: 'Diet', cats: ['Mediterranean', 'Green Mediterranean', 'Anti-Inflammatory', 'High Protein'] },
  { label: 'Type', cats: ['Breakfast', 'Dinner', 'Snack', 'Pasta', 'Soups and Stews'] },
  { label: 'Method', cats: ['Slow Cooker Recipes'] },
];

// --- Draggable Recipe Card ---

interface RecipeCardProps {
  recipe: Recipe;
  isDragging?: boolean;
}

function RecipeCard({ recipe, isDragging }: RecipeCardProps) {
  const stars = recipe.rating ? '★'.repeat(recipe.rating) : null;
  return (
    <div className={`${styles.recipeCard} ${isDragging ? styles.recipeCardDragging : ''}`}>
      {recipe.photo_path && (
        <img src={recipe.photo_path} alt={recipe.name} className={styles.recipePhoto} />
      )}
      <div className={styles.recipeCardBody}>
        <div className={styles.recipeName}>{recipe.name}</div>
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

function DraggableRecipeCard({ recipe }: { recipe: Recipe }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: recipe.id, data: { recipe } });
  return (
    <div ref={setNodeRef} {...listeners} {...attributes} style={{ opacity: isDragging ? 0.4 : 1 }}>
      <RecipeCard recipe={recipe} />
    </div>
  );
}

// --- Droppable Day Slot ---

interface DaySlotProps {
  day: WeekDay;
  onRemove: (slotId: string) => void;
}

function DaySlot({ day, onRemove }: DaySlotProps) {
  const { setNodeRef, isOver } = useDroppable({ id: day.date });
  return (
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
        <div className={styles.slotEmpty}>Drop here</div>
      )}
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
    pushToAnyList,
    toggleCategory,
    toggleBoolean,
  } = useMealPlanner();

  const [activeRecipe, setActiveRecipe] = useState<Recipe | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);

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
          <button
            className={styles.generateBtn}
            onClick={() => setShowGenerate(true)}
          >
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

      <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className={styles.body}>
          {/* Recipe list */}
          <div className={styles.recipePanel}>
            {loadingRecipes ? (
              <div className={`${styles.emptyState} pulse`}>Loading…</div>
            ) : recipes.length === 0 ? (
              <div className={styles.emptyState}>No recipes match these filters.</div>
            ) : (
              <div className={styles.recipeGrid}>
                {recipes.map(r => <DraggableRecipeCard key={r.id} recipe={r} />)}
              </div>
            )}
          </div>

          {/* Week schedule */}
          <div className={styles.weekPanel}>
            <div className={styles.weekTitle}>This Week — Dinners</div>
            {weekDays.map(day => (
              <DaySlot key={day.date} day={day} onRemove={removeRecipe} />
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
    </div>
  );

  return ReactDOM.createPortal(overlay, document.body);
}
