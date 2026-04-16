import { TEAMS, Team } from '../themes';
import { ThemeState } from '../hooks/useTheme';
import styles from './ThemePicker.module.css';

interface Props {
  theme: ThemeState;
  onClose: () => void;
}

export default function ThemePicker({ theme, onClose }: Props) {
  const { selection, autoTeam, setTheme } = theme;

  function pick(id: string) {
    setTheme(id);
    onClose();
  }

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.panel} onClick={e => e.stopPropagation()}>
        <div className={styles.title}>Theme</div>

        {/* Auto option */}
        <button
          className={`${styles.row} ${selection === 'auto' ? styles.rowActive : ''}`}
          onClick={() => pick('auto')}
        >
          <span
            className={styles.swatch}
            style={{
              background: autoTeam
                ? `linear-gradient(135deg, ${autoTeam.colors.surface} 50%, ${autoTeam.colors.accent} 50%)`
                : '#f59e0b',
            }}
          />
          <span className={styles.rowLabel}>
            Auto
            {autoTeam && (
              <span className={styles.rowSub}> — {autoTeam.label} season</span>
            )}
            {!autoTeam && (
              <span className={styles.rowSub}> — off-season</span>
            )}
          </span>
          {selection === 'auto' && <span className={styles.check}>✓</span>}
        </button>

        <div className={styles.divider} />

        {/* Team list */}
        {TEAMS.map((team: Team) => {
          const active = selection === team.id;
          return (
            <button
              key={team.id}
              className={`${styles.row} ${active ? styles.rowActive : ''}`}
              onClick={() => pick(team.id)}
            >
              <span
                className={styles.swatch}
                style={{
                  background: `linear-gradient(135deg, ${team.colors.surface} 50%, ${team.colors.accent} 50%)`,
                }}
              />
              <span className={styles.rowLabel}>{team.label}</span>
              {active && <span className={styles.check}>✓</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
