export interface TeamColors {
  bg: string;
  surface: string;
  surface2: string;
  border: string;
  accent: string;
  accentDim: string;
}

export interface Team {
  id: string;
  label: string;
  colors: TeamColors;
  // Season as [month (1-indexed), day]. Wraps year if start > end numerically.
  season: { start: [number, number]; end: [number, number] };
  // Lower = higher priority when multiple seasons overlap
  priority: number;
}

export const TEAMS: Team[] = [
  {
    id: 'phillies',
    label: 'Phillies',
    colors: {
      bg: '#0A1520',        // Very dark navy
      surface: '#0F2035',   // Dark powder blue
      surface2: '#173050',  // Medium powder blue
      border: '#173050',
      accent: '#800020',    // Phillies Maroon
      accentDim: '#4D0013',
    },
    season: { start: [4, 1], end: [10, 20] },
    priority: 1,
  },
  {
    id: 'eagles',
    label: 'Eagles',
    colors: {
      bg: '#001518',
      surface: '#003038',
      surface2: '#004C54',  // Midnight Green
      border: '#004C54',
      accent: '#C8CDCF',   // Eagles Silver
      accentDim: '#606870',
    },
    season: { start: [9, 1], end: [2, 15] },
    priority: 2,
  },
  {
    id: 'sixers',
    label: 'Sixers',
    colors: {
      bg: '#00102A',
      surface: '#002050',
      surface2: '#003580',
      border: '#003580',
      accent: '#ED174C',   // Sixers Red
      accentDim: '#8B0E2D',
    },
    season: { start: [10, 15], end: [6, 30] },
    priority: 3,
  },
  {
    id: 'ohio-state',
    label: 'Ohio State',
    colors: {
      bg: '#200000',
      surface: '#3A0000',
      surface2: '#5A0000',
      border: '#5A0000',
      accent: '#F5F5F5',   // White (max contrast on scarlet)
      accentDim: '#A0A0A0',
    },
    season: { start: [9, 1], end: [1, 20] },
    priority: 4,
  },
  {
    id: 'penn-state',
    label: 'Penn State',
    colors: {
      bg: '#000820',
      surface: '#001030',
      surface2: '#001848',
      border: '#001848',
      accent: '#8FAADC',   // Penn State light blue
      accentDim: '#3A5C9A',
    },
    season: { start: [9, 1], end: [1, 20] },
    priority: 5,
  },
  {
    id: 'flyers',
    label: 'Flyers',
    colors: {
      bg: '#111111',
      surface: '#1E1200',
      surface2: '#2D1800',
      border: '#2D1800',
      accent: '#F74902',   // Flyers Orange
      accentDim: '#7A2401',
    },
    season: { start: [10, 1], end: [6, 15] },
    priority: 6,
  },
  {
    id: 'stars',
    label: 'Stars',
    colors: {
      bg: '#001208',
      surface: '#002515',
      surface2: '#004030',
      border: '#004030',
      accent: '#C4A44B',   // Stars Gold
      accentDim: '#7A6430',
    },
    season: { start: [10, 1], end: [6, 15] },
    priority: 7,
  },
  {
    id: 'packers',
    label: 'Packers',
    colors: {
      bg: '#0D1508',
      surface: '#1A2812',
      surface2: '#203731',  // Packers Dark Green
      border: '#203731',
      accent: '#FFB612',   // Packers Gold
      accentDim: '#8C6A00',
    },
    season: { start: [9, 1], end: [2, 15] },
    priority: 8,
  },
];

export const DEFAULT_COLORS: TeamColors = {
  bg: '#111827',
  surface: '#1f2937',
  surface2: '#374151',
  border: '#374151',
  accent: '#f59e0b',
  accentDim: '#92400e',
};

function isInSeason(today: Date, start: [number, number], end: [number, number]): boolean {
  const m = today.getMonth() + 1;
  const d = today.getDate();
  const todayNum = m * 100 + d;
  const startNum = start[0] * 100 + start[1];
  const endNum = end[0] * 100 + end[1];
  if (startNum <= endNum) {
    return todayNum >= startNum && todayNum <= endNum;
  }
  return todayNum >= startNum || todayNum <= endNum;
}

export function getAutoTeam(today: Date = new Date()): Team | null {
  const active = TEAMS.filter(t => isInSeason(today, t.season.start, t.season.end));
  if (active.length === 0) return null;
  return active.sort((a, b) => a.priority - b.priority)[0];
}

export function getTeamById(id: string): Team | undefined {
  return TEAMS.find(t => t.id === id);
}
