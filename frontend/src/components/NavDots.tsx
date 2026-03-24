import { ViewName } from '../hooks/useViewCycle';
import styles from './NavDots.module.css';

interface Props {
  currentView: ViewName;
  goTo: (view: ViewName) => void;
  interactMode: boolean;
}

interface ViewDef {
  name: ViewName;
  label: string;
}

const VIEWS: ViewDef[] = [
  { name: 'home', label: 'Home' },
  { name: 'planning', label: 'Plan' },
  { name: 'household', label: 'House' },
  { name: 'ambient', label: 'Ambient' },
];

export default function NavDots({ currentView, goTo, interactMode }: Props) {
  return (
    <nav className={styles.navDots} role="navigation" aria-label="View navigation">
      {VIEWS.map(view => {
        const isActive = view.name === currentView;
        return (
          <button
            key={view.name}
            className={styles.dotWrapper}
            onClick={() => goTo(view.name)}
            aria-label={`Go to ${view.label} view`}
            aria-current={isActive ? 'page' : undefined}
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          >
            <div className={`${styles.dot} ${isActive ? styles.dotActive : ''}`} />
            <span
              className={`${styles.label} ${interactMode ? styles.labelVisible : ''} ${
                isActive ? styles.labelActive : ''
              }`}
            >
              {view.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
