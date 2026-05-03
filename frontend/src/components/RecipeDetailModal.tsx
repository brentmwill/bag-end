import { useEffect, useState } from 'react';
import { RecipeDetail } from '../types';
import styles from './RecipeDetailModal.module.css';

interface Props {
  recipeId: string;
  onClose: () => void;
  onStartCooking?: (recipeId: string) => void;
}

export default function RecipeDetailModal({ recipeId, onClose, onStartCooking }: Props) {
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/recipes/${recipeId}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        if (!cancelled) setRecipe(data as RecipeDetail);
      })
      .catch(e => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load recipe');
      });
    return () => { cancelled = true; };
  }, [recipeId]);

  const handleCookNow = () => {
    if (onStartCooking) onStartCooking(recipeId);
    onClose();
  };

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        {!recipe && !error && (
          <div className={`${styles.body} pulse`}>Loading…</div>
        )}
        {error && (
          <div className={styles.body}>
            <div className={styles.error}>Couldn't load recipe: {error}</div>
            <button className={styles.closeBtn} onClick={onClose}>Close</button>
          </div>
        )}
        {recipe && (
          <>
            <div className={styles.header}>
              <div className={styles.title}>{recipe.name}</div>
              <button className={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
            </div>
            <div className={styles.meta}>
              {recipe.prep_time && <span>Prep: {recipe.prep_time}</span>}
              {recipe.cook_time && <span>Cook: {recipe.cook_time}</span>}
              {recipe.servings && <span>Serves: {recipe.servings}</span>}
            </div>
            {recipe.categories.length > 0 && (
              <div className={styles.tags}>
                {recipe.categories.map(c => (
                  <span key={c} className={styles.tag}>{c}</span>
                ))}
              </div>
            )}
            <div className={styles.body}>
              <div className={styles.section}>
                <div className={styles.sectionLabel}>Ingredients</div>
                <ul className={styles.ingredientList}>
                  {recipe.ingredients.map(ing => (
                    <li key={ing.id}>{ing.display_text}</li>
                  ))}
                </ul>
              </div>
              <div className={styles.section}>
                <div className={styles.sectionLabel}>Directions</div>
                <ol className={styles.directionList}>
                  {recipe.steps.map(step => (
                    <li key={step.id}>{step.instruction}</li>
                  ))}
                </ol>
              </div>
              {recipe.notes && (
                <div className={styles.section}>
                  <div className={styles.sectionLabel}>Notes</div>
                  <p className={styles.notes}>{recipe.notes}</p>
                </div>
              )}
            </div>
            <div className={styles.actions}>
              {onStartCooking && (
                <button className={styles.cookNowBtn} onClick={handleCookNow}>
                  ▶ Cook this now
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
