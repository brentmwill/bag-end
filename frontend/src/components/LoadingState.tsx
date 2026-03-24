import type { CSSProperties } from 'react';

interface Props {
  message?: string;
  style?: CSSProperties;
}

const containerStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  gap: '1rem',
};

const dotContainerStyle: CSSProperties = {
  display: 'flex',
  gap: '0.5rem',
};

function Dot({ delay }: { delay: string }) {
  return (
    <div
      className="pulse"
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: 'var(--accent)',
        animationDelay: delay,
      }}
    />
  );
}

export default function LoadingState({ message = 'Loading...', style }: Props) {
  return (
    <div style={{ ...containerStyle, ...style }}>
      <div style={dotContainerStyle}>
        <Dot delay="0s" />
        <Dot delay="0.2s" />
        <Dot delay="0.4s" />
      </div>
      <span
        className="text-muted text-sm pulse"
        style={{ letterSpacing: '0.08em', textTransform: 'uppercase' }}
      >
        {message}
      </span>
    </div>
  );
}
