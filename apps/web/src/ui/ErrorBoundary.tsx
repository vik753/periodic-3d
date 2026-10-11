import type { ErrorInfo, ReactNode } from 'react';
import { Component } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { isChunkError, reloadForNewVersion } from '../lib/lazyChunk';

interface Props {
  children: ReactNode;
  fallback: ReactNode;
  /** A new value (the page address) clears the error: the next page gets a fresh try. */
  resetKey?: string;
}

interface State {
  error: Error | null;
}

/**
 * Keeps one failing part from blanking the whole site. A missing chunk after a deploy
 * reloads the page once (lib/lazyChunk.ts); any other error shows the fallback.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(error, info.componentStack);
    if (isChunkError(error)) reloadForNewVersion();
  }

  componentDidUpdate(previous: Props): void {
    if (this.state.error && previous.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render(): ReactNode {
    return this.state.error ? this.props.fallback : this.props.children;
  }
}

/** What a visitor sees instead of a failed part: what happened and two ways on. */
export function ErrorNotice({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className={
        compact
          ? 'pointer-events-auto fixed inset-x-3 bottom-3 z-10 rounded-[20px] bg-panel p-5 ring-1 ring-rim backdrop-blur-md sm:inset-x-auto sm:bottom-auto sm:right-5 sm:top-20 sm:w-[360px]'
          : 'fixed inset-0 z-0 flex items-center justify-center p-6'
      }
    >
      <div className={compact ? '' : 'max-w-sm rounded-[20px] bg-panel p-6 text-center ring-1 ring-rim'}>
        <p className="font-display text-lg font-semibold">{t('error.title')}</p>
        <p className="mt-2 text-sm leading-relaxed text-muted">{t('error.text')}</p>
        <div className={`mt-4 flex flex-wrap gap-2 ${compact ? '' : 'justify-center'}`}>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-full bg-gold px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-text"
          >
            {t('error.reload')}
          </button>
          <Link to="/" className="rounded-full px-4 py-2 text-sm text-text ring-1 ring-rim hover:ring-gold/60">
            {t('nav.toTable')}
          </Link>
        </div>
      </div>
    </div>
  );
}
