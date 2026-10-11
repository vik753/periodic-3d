import { lazy, Suspense, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';

import { pickName } from '../data/api';
import { useElements } from '../data/hooks';
import { ELEMENTS } from '../data/periodic';
import { isTouchFirst } from '../lib/device';
import { useAppStore } from '../state/store';
import { formatNumber } from './format';
import { Panel, Skeleton } from './Panel';

// Panels load with their scene; the table needs only the hint below.
const AboutPanel = lazy(() => import('./AboutPanel').then((module) => ({ default: module.AboutPanel })));
const CompoundPanel = lazy(() => import('./CompoundPanel').then((module) => ({ default: module.CompoundPanel })));
const ElementPanel = lazy(() => import('./ElementPanel').then((module) => ({ default: module.ElementPanel })));
const MaterialPanel = lazy(() => import('./MaterialPanel').then((module) => ({ default: module.MaterialPanel })));
const SetPanel = lazy(() => import('./SetPanel').then((module) => ({ default: module.SetPanel })));

function Loading() {
  return (
    <Panel label="">
      <Skeleton lines={5} />
    </Panel>
  );
}

/** Card of the magnified tile: readable facts, and on touch screens a button to open it. */
function TilePreview({ z }: { z: number }) {
  const { t, i18n } = useTranslation();
  const elements = useElements();
  const setHoveredZ = useAppStore((state) => state.setHoveredZ);
  const cell = ELEMENTS[z - 1];
  if (!cell) return null;
  const summary = elements.data?.elements.find((element) => element.z === z);
  const name = pickName(summary?.names, i18n.language);
  const touch = isTouchFirst();
  return (
    <div
      role="status"
      className="pointer-events-auto flex w-full items-center gap-4 rounded-2xl bg-panel px-4 py-3 ring-1 ring-rim backdrop-blur-md sm:w-auto sm:min-w-[22rem]"
    >
      <div className="text-center">
        <p className="text-xs tabular-nums text-muted">{z}</p>
        <p className="font-display text-3xl font-semibold leading-none">{cell.symbol}</p>
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-base font-medium">{name || cell.symbol}</p>
        <p className="truncate text-xs text-muted">
          {t(`category.${cell.category}`)}
          {summary?.mass != null && <> · {formatNumber(summary.mass, i18n.language, 3)}</>}
        </p>
        {summary && summary.compoundCount > 0 && (
          <p className="truncate text-xs text-muted">{t('element.compoundCount', { count: summary.compoundCount })}</p>
        )}
      </div>
      {touch ? (
        <Link
          to={`/e/${cell.symbol}`}
          onClick={() => setHoveredZ(null)}
          className="shrink-0 rounded-full bg-gold px-3 py-1.5 text-sm font-semibold text-ink"
        >
          {t('preview.open')}
        </Link>
      ) : (
        <p className="shrink-0 text-xs text-muted">{t('preview.click')}</p>
      )}
    </div>
  );
}

/** The hovered element, kept for a moment while the pointer crosses the gap between tiles. */
function useLingeringHover(delayMs = 350): number | null {
  const hoveredZ = useAppStore((state) => state.hoveredZ);
  const [shown, setShown] = useState<number | null>(hoveredZ);
  useEffect(() => {
    if (hoveredZ != null) {
      setShown(hoveredZ);
      return undefined;
    }
    const timer = window.setTimeout(() => setShown(null), delayMs);
    return () => window.clearTimeout(timer);
  }, [hoveredZ, delayMs]);
  return hoveredZ ?? shown;
}

/**
 * The chosen elements and the way to their shared compounds. It sits at the very bottom
 * of the screen: the hover card and the hint appear above it, so the buttons never move
 * under the pointer. The buttons are 40 px high: easy to hit with a mouse or a finger.
 */
function SelectionBar({ selection }: { selection: readonly number[] }) {
  const { t } = useTranslation();
  const clearSelection = useAppStore((state) => state.clearSelection);
  const symbols = selection.map((z) => ELEMENTS[z - 1]?.symbol);
  return (
    <div className="rise-in pointer-events-auto flex w-full items-center gap-2 rounded-full bg-panel py-2 pl-5 pr-2 ring-1 ring-gold/40 backdrop-blur-md sm:w-auto sm:gap-3">
      <p className="min-w-0 flex-1 truncate text-sm sm:flex-none">
        {t('selection.count', { count: selection.length })}{' '}
        <span className="font-display font-medium text-gold">{symbols.join(' ')}</span>
      </p>
      <Link
        to={`/set/${symbols.join('-')}`}
        className="shrink-0 rounded-full bg-gold px-4 py-2.5 text-sm font-semibold leading-5 text-ink transition-colors hover:bg-text"
      >
        {t('selection.show')}
      </Link>
      <button
        type="button"
        onClick={clearSelection}
        className="shrink-0 rounded-full px-4 py-2.5 text-sm leading-5 text-muted ring-1 ring-rim transition-colors hover:text-text"
      >
        {t('selection.clear')}
      </button>
    </div>
  );
}

function TableHint() {
  const { t } = useTranslation();
  const hoveredZ = useLingeringHover();
  const selection = useAppStore((state) => state.selection);
  const selectMode = useAppStore((state) => state.selectMode);
  const setSelectMode = useAppStore((state) => state.setSelectMode);
  // The column grows upwards from the bottom edge: what appears on hover goes on top.
  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-3 z-10 flex flex-col items-start gap-2 sm:left-5 sm:right-auto sm:bottom-5 sm:max-w-xl">
      {hoveredZ != null && <TilePreview z={hoveredZ} />}
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
          {t(selectMode ? 'hint.select' : isTouchFirst() ? 'hint.tableTouch' : 'hint.table')}
        </p>
      </div>
      {selection.length > 0 && <SelectionBar selection={selection} />}
    </div>
  );
}

function ScenePanel() {
  const scene = useAppStore((state) => state.scene);
  const location = useLocation();
  if (location.pathname === '/about') return <AboutPanel />;
  if (scene.kind === 'element')
    return (
      <ElementPanel
        key={`${scene.symbol}/${scene.partner ?? ''}/${scene.predicted ? 'p' : ''}`}
        symbol={scene.symbol}
        partner={scene.partner}
        predicted={scene.predicted}
      />
    );
  if (scene.kind === 'compound') return <CompoundPanel key={scene.id} id={scene.id} />;
  if (scene.kind === 'material') return <MaterialPanel key={scene.id} id={scene.id} />;
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
