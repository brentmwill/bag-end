import { useState } from 'react';
import { Filters } from '../hooks/useMealPlanner';
import { GeneratedRecipe, Recipe } from '../types';
import styles from './GenerateRecipeModal.module.css';

interface Props {
  filters: Filters;
  onSaved: (recipe: Recipe) => void;
  onClose: () => void;
}

export default function GenerateRecipeModal({ filters, onSaved, onClose }: Props) {
  const [status, setStatus] = useState<'idle' | 'generating' | 'review' | 'saving' | 'error'>('idle');
  const [generated, setGenerated] = useState<GeneratedRecipe | null>(null);
  const [error, setError] = useState('');

  const generate = async () => {
    setStatus('generating');
    setError('');
    try {
      const res = await fetch('/api/recipes/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          categories: filters.categories,
          pregnancy_safe: filters.pregnancy_safe || null,
          baby_friendly: filters.baby_friendly || null,
          freezable: filters.freezable || null,
          save: false,
        }),
      });
      if (!res.ok) throw new Error('Generation failed');
      const data: GeneratedRecipe = await res.json();
      setGenerated(data);
      setStatus('review');
    } catch {
      setError('Failed to generate recipe. Try again.');
      setStatus('error');
    }
  };

  const approve = async () => {
    if (!generated) return;
    setStatus('saving');
    try {
      const res = await fetch('/api/recipes/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          categories: filters.categories,
          pregnancy_safe: filters.pregnancy_safe || null,
          baby_friendly: filters.baby_friendly || null,
          freezable: filters.freezable || null,
          save: true,
          // Pass name hint so it generates the same recipe
        }),
      });
      if (!res.ok) throw new Error('Save failed');
      const saved = await res.json();
      onSaved(saved as Recipe);
    } catch {
      setError('Failed to save. Try again.');
      setStatus('review');
    }
  };

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.header}>
          <span className={styles.title}>Generate Recipe</span>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        {(status === 'idle' || status === 'error') && (
          <div className={styles.body}>
            <div className={styles.context}>
              {filters.categories.length > 0 ? (
                <span>Style: <strong>{filters.categories.join(', ')}</strong></span>
              ) : (
                <span className={styles.muted}>No filters active — any recipe</span>
              )}
              {filters.pregnancy_safe && <span className={styles.tag}>Pregnancy-safe</span>}
              {filters.baby_friendly && <span className={styles.tag}>Baby-friendly</span>}
              {filters.freezable && <span className={styles.tag}>Freezable</span>}
            </div>
            {error && <div className={styles.error}>{error}</div>}
            <button className={styles.generateBtn} onClick={generate}>
              Generate Recipe
            </button>
          </div>
        )}

        {status === 'generating' && (
          <div className={styles.body}>
            <div className={`${styles.muted} pulse`}>Generating recipe…</div>
          </div>
        )}

        {(status === 'review' || status === 'saving') && generated && (
          <div className={styles.body}>
            <div className={styles.recipeName}>{generated.name}</div>
            <div className={styles.recipeMeta}>
              {generated.prep_time && <span>Prep: {generated.prep_time}</span>}
              {generated.cook_time && <span>Cook: {generated.cook_time}</span>}
              {generated.servings && <span>Serves: {generated.servings}</span>}
            </div>
            <div className={styles.ingredientList}>
              {generated.ingredients.map((ing, i) => (
                <div key={i} className={styles.ingredient}>{ing.display_text}</div>
              ))}
            </div>
            <div className={styles.actions}>
              <button
                className={styles.discardBtn}
                onClick={() => { setGenerated(null); setStatus('idle'); }}
                disabled={status === 'saving'}
              >
                Discard
              </button>
              <button
                className={styles.regenerateBtn}
                onClick={generate}
                disabled={status === 'saving'}
              >
                Regenerate
              </button>
              <button
                className={styles.approveBtn}
                onClick={approve}
                disabled={status === 'saving'}
              >
                {status === 'saving' ? 'Saving…' : 'Add to Recipes'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
