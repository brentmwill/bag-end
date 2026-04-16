import { useState, useEffect, useCallback } from 'react';
import {
  Team,
  TeamColors,
  DEFAULT_COLORS,
  getAutoTeam,
  getTeamById,
} from '../themes';

const STORAGE_KEY = 'bag-end-theme';

function applyColors(colors: TeamColors) {
  const root = document.documentElement;
  root.style.setProperty('--bg', colors.bg);
  root.style.setProperty('--surface', colors.surface);
  root.style.setProperty('--surface-2', colors.surface2);
  root.style.setProperty('--border', colors.border);
  root.style.setProperty('--accent', colors.accent);
  root.style.setProperty('--accent-dim', colors.accentDim);
}

export interface ThemeState {
  activeTeam: Team | null;
  autoTeam: Team | null;
  selection: string;
  setTheme: (selection: string) => void;
}

export function useTheme(): ThemeState {
  const autoTeam = getAutoTeam();

  const [selection, setSelectionState] = useState<string>(() => {
    return localStorage.getItem(STORAGE_KEY) ?? 'auto';
  });

  const activeTeam: Team | null =
    selection === 'auto' ? autoTeam : (getTeamById(selection) ?? autoTeam);

  useEffect(() => {
    applyColors(activeTeam?.colors ?? DEFAULT_COLORS);
  }, [activeTeam?.id]);

  const setTheme = useCallback((next: string) => {
    localStorage.setItem(STORAGE_KEY, next);
    setSelectionState(next);
  }, []);

  return { activeTeam, autoTeam, selection, setTheme };
}
