import { useState, useEffect } from 'react';
import { GlanceData } from '../types';
import styles from './AmbientView.module.css';

interface Props {
  data: GlanceData | null;
}

interface TimeState {
  hhmm: string;
  ss: string;
  date: string;
}

function getTimeState(): TimeState {
  const now = new Date();
  const hhmm = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const ss = now.toLocaleTimeString([], { second: '2-digit' }).replace(/^.*:/, '').padStart(2, '0');
  const date = now.toLocaleDateString([], {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  return { hhmm, ss, date };
}

export default function AmbientView({ data }: Props) {
  const [timeState, setTimeState] = useState<TimeState>(getTimeState);

  useEffect(() => {
    const id = setInterval(() => {
      setTimeState(getTimeState());
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const word = data?.ambient?.word_of_day ?? null;

  return (
    <div className={`${styles.container} view-enter`}>
      {/* Clock */}
      <div className={styles.clockSection}>
        <div>
          <span className={styles.clock}>{timeState.hhmm}</span>
          <span className={styles.clockSeconds}>:{timeState.ss}</span>
        </div>
        <div className={styles.date}>{timeState.date}</div>
      </div>

      {/* Word of the Day */}
      {word ? (
        <div className={styles.wordCard}>
          <div className={styles.wordHeader}>
            <span className={styles.word}>{word.word}</span>
            {word.pronunciation && (
              <span className={styles.pronunciation}>{word.pronunciation}</span>
            )}
          </div>
          <div className={styles.partOfSpeech}>Word of the Day</div>
          <div className={styles.definition}>{word.definition}</div>
          {word.etymology && (
            <div className={styles.etymology}>
              <span className={styles.etymologyLabel}>Etymology: </span>
              {word.etymology}
            </div>
          )}
          {word.example && (
            <div className={styles.example}>"{word.example}"</div>
          )}
        </div>
      ) : (
        <div className={styles.wordPlaceholder}>
          <div className={styles.wordPlaceholderInner}>
            <p className={styles.wordPlaceholderText}>No word of the day</p>
          </div>
        </div>
      )}

      {/* Branding */}
      <div className={styles.branding}>Bag End</div>
    </div>
  );
}
