import styles from './InteractOverlay.module.css';

interface Props {
  advance: () => void;
  retreat: () => void;
  onOpenThemePicker: () => void;
}

export default function InteractOverlay({ advance, retreat, onOpenThemePicker }: Props) {
  return (
    <div className={styles.overlay} aria-hidden="true">
      {/* Top banner */}
      <div className={styles.banner}>
        <span className={styles.bannerText}>Interact mode — auto-cycle paused</span>
        <button
          className={styles.themeBtn}
          onClick={onOpenThemePicker}
          aria-label="Change theme"
        >
          ◈ Theme
        </button>
      </div>

      {/* Left arrow */}
      <button
        className={styles.arrowLeft}
        onClick={retreat}
        aria-label="Previous view"
      >
        ◀
      </button>

      {/* Right arrow */}
      <button
        className={styles.arrowRight}
        onClick={advance}
        aria-label="Next view"
      >
        ▶
      </button>
    </div>
  );
}
