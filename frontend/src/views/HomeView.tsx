import { useState, useEffect } from 'react';
import { GlanceData, CalendarEvent, CommuteTile } from '../types';
import styles from './HomeView.module.css';

interface Props {
  data: GlanceData | null;
  onStartCooking?: (recipeId: string) => void;
  onRefreshGlance?: () => Promise<void>;
}

function weatherEmoji(code: number): string {
  if (code === 0) return '☀️';
  if (code <= 3) return '🌤️';
  if (code <= 48) return '🌫️';
  if (code <= 67) return '🌧️';
  if (code <= 77) return '🌨️';
  if (code <= 82) return '🌦️';
  if (code === 95) return '⛈️';
  return '🌡️';
}

function formatTime(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatForecastDate(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString([], { weekday: 'short' });
}

function localDateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isTodayEvent(event: CalendarEvent): boolean {
  const todayKey = localDateKey(new Date());
  // All-day events have start as 'YYYY-MM-DD'. Don't pass through new Date(),
  // which interprets bare dates as UTC and can shift the day for Eastern users.
  if (event.all_day) {
    return event.start.startsWith(todayKey);
  }
  return localDateKey(new Date(event.start)) === todayKey;
}

function CommuteTileComponent({ tile }: { tile: CommuteTile | null }) {
  return (
    <div className={styles.commuteTile}>
      <span className={styles.commuteTileLabel}>
        {tile ? tile.label : '—'}
      </span>
      {tile ? (
        <>
          <div>
            <span className={styles.commuteTileDuration}>{tile.duration_min}</span>
            <span className={styles.commuteTileDurationUnit}> min</span>
          </div>
          <span className={styles.commuteTileDistance}>{tile.distance_km.toFixed(1)} km</span>
          {tile.primary_road && (
            <span className={styles.commuteTileRoute}>via {tile.primary_road}</span>
          )}
        </>
      ) : (
        <span className={styles.commuteTileDuration}>--</span>
      )}
    </div>
  );
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function HomeView({ data, onStartCooking, onRefreshGlance }: Props) {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );
  const [refreshing, setRefreshing] = useState(false);

  const handleRefreshCommute = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await fetch('/api/commute/refresh', { method: 'POST' });
      if (onRefreshGlance) await onRefreshGlance();
    } catch {
      // swallow — last-known tiles stay rendered
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const home = data?.home ?? null;
  const weather = home?.weather ?? null;
  const forecast = weather?.forecast.slice(0, 3) ?? [];
  const commuteTiles: (CommuteTile | null)[] = home?.commute_tiles
    ? [
        home.commute_tiles[0] ?? null,
        home.commute_tiles[1] ?? null,
        home.commute_tiles[2] ?? null,
        home.commute_tiles[3] ?? null,
      ]
    : [null, null, null, null];

  const todayEvents = (home?.calendar_events ?? [])
    .filter(isTodayEvent)
    .slice(0, 4);

  return (
    <div className={`${styles.container} view-enter`}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.viewLabel}>Home</span>
        <span className={styles.clock}>{time}</span>
      </div>

      {/* Tonight's Meal */}
      <div className={styles.mealCard}>
        <div className={styles.mealLabel}>Tonight's Dinner</div>
        {home?.tonight_meal ? (
          <div className={styles.mealRow}>
            <div className={styles.mealName}>{home.tonight_meal.name}</div>
            {onStartCooking && (
              <button
                className={styles.cookBtn}
                onClick={() => onStartCooking(home.tonight_meal!.recipe_id)}
              >
                ▶ Cook
              </button>
            )}
          </div>
        ) : (
          <div className={styles.mealEmpty}>No dinner planned</div>
        )}
      </div>

      {/* Weather */}
      <div className={styles.weatherCard}>
        {weather ? (
          <>
            <div className={styles.weatherCurrent}>
              <span className={styles.weatherEmoji}>
                {weatherEmoji(weather.current.weathercode)}
              </span>
              <div>
                <div>
                  <span className={styles.weatherTemp}>
                    {Math.round(weather.current.temp)}
                  </span>
                  <span className={styles.weatherTempUnit}>°F</span>
                </div>
                <div className={styles.weatherWind}>
                  Wind {Math.round(weather.current.windspeed)} mph
                </div>
              </div>
            </div>
            <div className={styles.weatherForecast}>
              {forecast.map(day => (
                <div key={day.date} className={styles.forecastDay}>
                  <span className={styles.forecastDate}>{formatForecastDate(day.date)}</span>
                  <span className={styles.forecastEmoji}>{weatherEmoji(day.code)}</span>
                  <span className={styles.forecastTemps}>
                    <span className={styles.forecastHigh}>{Math.round(day.max)}°</span>
                    {' / '}
                    {Math.round(day.min)}°
                  </span>
                  {day.precip_prob > 10 && (
                    <span className={styles.forecastPrecip}>{day.precip_prob}%</span>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className={`${styles.cardLabel} pulse`}>Weather unavailable</div>
        )}
      </div>

      {/* Commute */}
      <div className={styles.commuteCard}>
        <div className={styles.commuteHeader}>
          <span className={styles.cardLabel}>Commute</span>
          <span className={styles.commuteMeta}>
            {(() => {
              const stamps = commuteTiles
                .filter((t): t is CommuteTile => !!t)
                .map(t => new Date(t.updated_at).getTime());
              if (stamps.length === 0) return null;
              const oldest = Math.min(...stamps);
              return (
                <span className={styles.commuteUpdated}>
                  Updated {formatRelative(new Date(oldest).toISOString())}
                </span>
              );
            })()}
            <button
              className={styles.commuteRefreshBtn}
              onClick={handleRefreshCommute}
              disabled={refreshing}
              aria-label="Refresh commute"
              title="Refresh commute"
            >
              {refreshing ? '…' : '↻'}
            </button>
          </span>
        </div>
        <div className={styles.commuteGrid}>
          {commuteTiles.map((tile, i) => (
            <CommuteTileComponent key={tile?.label ?? i} tile={tile} />
          ))}
        </div>
      </div>

      {/* Calendar Events */}
      <div className={styles.calendarCard}>
        <div className={styles.cardLabel}>Today</div>
        {todayEvents.length > 0 ? (
          <div className={styles.eventList}>
            {todayEvents.map(event => (
              <div key={event.id} className={styles.eventItem}>
                <span className={styles.eventTime}>
                  {event.all_day ? 'All day' : formatTime(event.start)}
                </span>
                <span className={styles.eventTitle}>{event.title}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.emptyState}>No events today</div>
        )}
      </div>

      {/* Digest */}
      {home?.digest_snippet && (
        <div className={styles.digestCard}>
          <div className={styles.cardLabel}>Digest</div>
          <p className={styles.digestText}>{home.digest_snippet}</p>
        </div>
      )}
    </div>
  );
}
