import type { CSSProperties } from 'react';
import { useGlanceData } from './hooks/useGlanceData';
import { useViewCycle } from './hooks/useViewCycle';
import ViewContainer from './components/ViewContainer';
import NavDots from './components/NavDots';
import InteractOverlay from './components/InteractOverlay';

const appRootStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  background: 'var(--bg)',
};

export default function App() {
  const { data, loading } = useGlanceData();
  const {
    currentView,
    interactMode,
    advance,
    retreat,
    goTo,
    activateInteract,
  } = useViewCycle();

  return (
    <div
      style={appRootStyle}
      onMouseMove={activateInteract}
      onClick={activateInteract}
    >
      <ViewContainer currentView={currentView} data={data} loading={loading} />

      <NavDots
        currentView={currentView}
        goTo={goTo}
        interactMode={interactMode}
      />

      {interactMode && (
        <InteractOverlay advance={advance} retreat={retreat} />
      )}
    </div>
  );
}
