import { lazy, Suspense } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';

import { ELEMENTS } from '../data/periodic';
import { useAppStore } from '../state/store';
import { Panel, Skeleton } from './Panel';

// Panels load with their scene; the table needs only the hint below.
const AboutPanel = lazy(() => import('./AboutPanel').then((module) => ({ default: module.AboutPanel })));
const CompoundPanel = lazy(() => import('./CompoundPanel').then((module) => ({ default: module.CompoundPanel })));
const ElementPanel = lazy(() => import('./ElementPanel').then((module) => ({ default: module.ElementPanel })));
const SetPanel = lazy(() => import('./SetPanel').then((module) => ({ default: module.SetPanel })));

function Loading() {
  return (
    <Panel label="">
      <Skeleton lines={5} />
    </Panel>
  );
}

function TableHint() {
  const { t } = useTranslation();
  const selection = useAppStore((state) => state.selection);
  const clearSelection = useAppStore((state) => state.clearSelection);
  const selectMode = useAppStore((state) => state.selectMode);
  const setSelectMode = useAppStore((state) => state.setSelectMode);
  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-3 z-10 flex flex-col items-start gap-2 sm:left-5 sm:right-auto sm:bottom-5 sm:max-w-md">
      {selection.length > 0 && (
        <div className="pointer-events-auto flex items-center gap-3 rounded-full bg-panel py-1.5 pl-4 pr-1.5 ring-1 ring-gold/40 backdrop-blur-md">
          <span className="text-sm">{t('selection.count', { count: selection.length })}</span>
          <span className="font-display text-sm font-medium text-gold">
            {selection.map((z) => ELEMENTS[z - 1]?.symbol).join(' ')}
          </span>
          <Link
            to={`/set/${selection.map((z) => ELEMENTS[z - 1]?.symbol).join('-')}`}
            className="rounded-full bg-gold px-3 py-1 text-xs font-semibold text-ink transition-colors hover:bg-text"
          >
            {t('selection.show')}
          </Link>
          <button
            type="button"
            onClick={clearSelection}
            className="rounded-full px-3 py-1 text-xs text-muted ring-1 ring-rim hover:text-text"
          >
            {t('selection.clear')}
          </button>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          aria-pressed={selectMode}
          onClick={() => setSelectMode(!selectMode)}
          className={`pointer-events-auto rounded-full px-3 py-1.5 text-sm ring-1 backdrop-blur-md transition-colors ${
            selectMode ? 'bg-gold font-semibold text-ink ring-gold' : 'bg-panel text-text ring-rim hover:ring-gold/60'
          }`}
        >
          {t(selectMode ? 'selection.modeOn' : 'selection.mode')}
        </button>
        <p className="rounded-2xl bg-panel/60 px-4 py-2 text-sm text-muted backdrop-blur-sm">
          {t(selectMode ? 'hint.select' : 'hint.table')}
        </p>
      </div>
    </div>
  );
}

function ScenePanel() {
  const scene = useAppStore((state) => state.scene);
  const location = useLocation();
  if (location.pathname === '/about') return <AboutPanel />;
  if (scene.kind === 'element')
    return <ElementPanel key={`${scene.symbol}/${scene.partner ?? ''}`} symbol={scene.symbol} partner={scene.partner} />;
  if (scene.kind === 'compound') return <CompoundPanel key={scene.id} id={scene.id} />;
  if (scene.kind === 'set') return <SetPanel symbols={scene.symbols} />;
  return <TableHint />;
}

export function InfoPanel() {
  return (
    <Suspense fallback={<Loading />}>
      <ScenePanel />
    </Suspense>
  );
}
