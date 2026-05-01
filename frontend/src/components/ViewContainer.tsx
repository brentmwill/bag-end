import type { CSSProperties } from 'react';
import { GlanceData } from '../types';
import { ViewName } from '../hooks/useViewCycle';
import HomeView from '../views/HomeView';
import PlanningView from '../views/PlanningView';
import CalendarView from '../views/CalendarView';
import HouseholdView from '../views/HouseholdView';
import AmbientView from '../views/AmbientView';
import LoadingState from './LoadingState';

interface Props {
  currentView: ViewName;
  data: GlanceData | null;
  loading: boolean;
  onStartCooking?: (recipeId: string) => void;
}

const containerStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  overflow: 'hidden',
};

export default function ViewContainer({ currentView, data, loading, onStartCooking }: Props) {
  if (loading && data === null) {
    return (
      <div style={containerStyle}>
        <LoadingState message="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {currentView === 'home' && <HomeView data={data} onStartCooking={onStartCooking} />}
      {currentView === 'planning' && <PlanningView data={data} />}
      {currentView === 'calendar' && <CalendarView />}
      {currentView === 'household' && <HouseholdView data={data} />}
      {currentView === 'ambient' && <AmbientView data={data} />}
    </div>
  );
}
