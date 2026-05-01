import { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { RecipeDetail } from '../types';
import styles from './CookingModeOverlay.module.css';

interface Props {
  recipeId: string;
  onClose: () => void;
}

export default function CookingModeOverlay({ recipeId, onClose }: Props) {
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [marking, setMarking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/recipes/${recipeId}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: RecipeDetail) => {
        if (!cancelled) setRecipe(data);
      })
      .catch(err => {
        if (!cancelled) setLoadError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [recipeId]);

  const steps = recipe?.steps ?? [];
  const sortedSteps = [...steps].sort((a, b) => a.step_number - b.step_number);
  const currentStep = sortedSteps[stepIndex] ?? null;
  const isFirst = stepIndex === 0;
  const isLast = stepIndex >= sortedSteps.length - 1;

  const handlePrev = () => {
    if (!isFirst) setStepIndex(i => i - 1);
  };

  const handleNext = () => {
    if (!isLast) setStepIndex(i => i + 1);
  };

  const handleDone = async () => {
    setMarking(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      await fetch(`/api/recipes/${recipeId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ last_made_date: today }),
      });
    } catch {
      // Non-blocking — close anyway. Recommendations will pick it up next time.
    } finally {
      setMarking(false);
      onClose();
    }
  };

  const overlay = (
    <div className={styles.overlay}>
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <div className={styles.recipeName}>{recipe?.name ?? 'Loading…'}</div>
          {sortedSteps.length > 0 && (
            <div className={styles.stepCounter}>
              Step {stepIndex + 1} of {sortedSteps.length}
            </div>
          )}
        </div>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Exit cooking mode">
          ✕
        </button>
      </div>

      {loadError && (
        <div className={styles.errorState}>Could not load recipe: {loadError}</div>
      )}

      {!loadError && recipe && sortedSteps.length === 0 && (
        <div className={styles.errorState}>This recipe has no steps recorded.</div>
      )}

      {!loadError && recipe && sortedSteps.length > 0 && (
        <>
          <div className={styles.body}>
            <div className={styles.stepBox}>
              <div className={styles.stepNumber}>{currentStep?.step_number}</div>
              <div className={styles.stepInstruction}>{currentStep?.instruction}</div>
            </div>

            <div className={styles.ingredientsRail}>
              <div className={styles.ingredientsLabel}>Ingredients</div>
              <ul className={styles.ingredientList}>
                {recipe.ingredients.map(ing => (
                  <li key={ing.id} className={styles.ingredientItem}>
                    {ing.display_text}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className={styles.footer}>
            <button
              className={styles.navBtn}
              onClick={handlePrev}
              disabled={isFirst}
            >
              ‹ Prev
            </button>
            {isLast ? (
              <button
                className={`${styles.navBtn} ${styles.doneBtn}`}
                onClick={handleDone}
                disabled={marking}
              >
                {marking ? 'Saving…' : 'Done ✓'}
              </button>
            ) : (
              <button className={styles.navBtn} onClick={handleNext}>
                Next ›
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );

  return ReactDOM.createPortal(overlay, document.body);
}
