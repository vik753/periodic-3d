import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

/** Glass side panel on wide screens, bottom sheet on phones. */
export function Panel({ children, label }: { children: ReactNode; label: string }) {
  return (
    <aside
      aria-label={label}
      className="pointer-events-auto fixed inset-x-3 bottom-3 z-10 max-h-[46vh] overflow-y-auto rounded-[20px] bg-panel p-5 ring-1 ring-rim backdrop-blur-md sm:inset-x-auto sm:bottom-auto sm:right-5 sm:top-20 sm:max-h-[calc(100vh-7rem)] sm:w-[360px]"
    >
      {children}
    </aside>
  );
}

export function Row({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-white/5 py-2 first:border-t-0">
      <dt className="text-sm text-muted">{term}</dt>
      <dd className="text-right text-sm tabular-nums text-text">{children}</dd>
    </div>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-text">{title}</h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

export function BackButton() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const goBack = () => {
    const index = (window.history.state as { idx?: number } | null)?.idx ?? 0;
    if (index > 0) navigate(-1);
    else navigate('/');
  };
  return (
    <button
      type="button"
      onClick={goBack}
      className="mb-4 rounded-full px-3 py-1 text-sm text-muted ring-1 ring-rim transition-colors hover:text-text"
    >
      {t('nav.back')}
    </button>
  );
}

/** Placeholder lines while data loads. */
export function Skeleton({ lines = 4 }: { lines?: number }) {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t('status.loading')} className="mt-4 space-y-3">
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className="h-3 rounded-full bg-white/[0.07] motion-safe:animate-pulse"
          style={{ width: `${88 - index * 13}%` }}
        />
      ))}
    </div>
  );
}

export function StatusNote({ children }: { children: ReactNode }) {
  return <p className="mt-6 text-xs leading-relaxed text-muted">{children}</p>;
}
