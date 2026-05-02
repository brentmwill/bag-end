import { useState } from 'react';
import type { CSSProperties } from 'react';
import { useGlanceData } from './hooks/useGlanceData';
import { useViewCycle } from './hooks/useViewCycle';
import { useTheme } from './hooks/useTheme';
import ViewContainer from './components/ViewContainer';
import NavDots from './components/NavDots';
import InteractOverlay from './components/InteractOverlay';
import ThemePicker from './components/ThemePicker';
import CookingModeOverlay from './components/CookingModeOverlay';

const appRootStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  background: 'var(--bg)',
};

export default function App() {
  const { data, loading, refresh } = useGlanceData();
  const {
    currentView,
    interactMode,
    advance,
    retreat,
    goTo,
    activateInteract,
  } = useViewCycle();
  const theme = useTheme();
  const [themePickerOpen, setThemePickerOpen] = useState(false);
  const [cookingRecipeId, setCookingRecipeId] = useState<string | null>(null);

  return (
    <div
      style={appRootStyle}
      onMouseMove={activateInteract}
      onClick={activateInteract}
    >
      <ViewContainer
        currentView={currentView}
        data={data}
        loading={loading}
        onStartCooking={setCookingRecipeId}
        onRefreshGlance={refresh}
      />

      <NavDots
        currentView={currentView}
        goTo={goTo}
        interactMode={interactMode}
      />

      {interactMode && (
        <InteractOverlay
          advance={advance}
          retreat={retreat}
          onOpenThemePicker={() => setThemePickerOpen(true)}
        />
      )}

      {themePickerOpen && (
        <ThemePicker
          theme={theme}
          onClose={() => setThemePickerOpen(false)}
        />
      )}

      {cookingRecipeId && (
        <CookingModeOverlay
          recipeId={cookingRecipeId}
          onClose={() => setCookingRecipeId(null)}
        />
      )}
    </div>
  );
}
