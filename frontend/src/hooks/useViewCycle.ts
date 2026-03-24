import { useState, useEffect, useRef, useCallback } from 'react';

export type ViewName = 'home' | 'planning' | 'household' | 'ambient';

const VIEWS: ViewName[] = ['home', 'planning', 'household', 'ambient'];
const CYCLE_MS = 45000;
const INTERACT_TIMEOUT_MS = 30000;

interface UseViewCycleResult {
  currentView: ViewName;
  interactMode: boolean;
  advance: () => void;
  retreat: () => void;
  goTo: (view: ViewName) => void;
  activateInteract: () => void;
  deactivateInteract: () => void;
}

export function useViewCycle(): UseViewCycleResult {
  const [currentView, setCurrentView] = useState<ViewName>('home');
  const [interactMode, setInteractMode] = useState(false);

  const cycleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const interactModeRef = useRef(false);

  const clearCycleTimer = () => {
    if (cycleTimerRef.current !== null) {
      clearInterval(cycleTimerRef.current);
      cycleTimerRef.current = null;
    }
  };

  const clearInactivityTimer = () => {
    if (inactivityTimerRef.current !== null) {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }
  };

  const deactivateInteract = useCallback(() => {
    interactModeRef.current = false;
    setInteractMode(false);
    clearInactivityTimer();

    // Resume cycle
    cycleTimerRef.current = setInterval(() => {
      setCurrentView(prev => {
        const idx = VIEWS.indexOf(prev);
        return VIEWS[(idx + 1) % VIEWS.length];
      });
    }, CYCLE_MS);
  }, []);

  const activateInteract = useCallback(() => {
    interactModeRef.current = true;
    setInteractMode(true);

    // Pause cycle
    clearCycleTimer();

    // Reset inactivity timer
    clearInactivityTimer();
    inactivityTimerRef.current = setTimeout(() => {
      deactivateInteract();
    }, INTERACT_TIMEOUT_MS);
  }, [deactivateInteract]);

  const advance = useCallback(() => {
    setCurrentView(prev => {
      const idx = VIEWS.indexOf(prev);
      return VIEWS[(idx + 1) % VIEWS.length];
    });
  }, []);

  const retreat = useCallback(() => {
    setCurrentView(prev => {
      const idx = VIEWS.indexOf(prev);
      return VIEWS[(idx - 1 + VIEWS.length) % VIEWS.length];
    });
  }, []);

  const goTo = useCallback((view: ViewName) => {
    setCurrentView(view);
  }, []);

  // Start the auto-cycle on mount
  useEffect(() => {
    cycleTimerRef.current = setInterval(() => {
      if (!interactModeRef.current) {
        setCurrentView(prev => {
          const idx = VIEWS.indexOf(prev);
          return VIEWS[(idx + 1) % VIEWS.length];
        });
      }
    }, CYCLE_MS);

    return () => {
      clearCycleTimer();
      clearInactivityTimer();
    };
  }, []);

  return {
    currentView,
    interactMode,
    advance,
    retreat,
    goTo,
    activateInteract,
    deactivateInteract,
  };
}
