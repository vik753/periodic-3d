import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';

import { DEMO_COMPOUNDS, demoCompound } from '../data/demo';
import { condensedConfiguration, elementBySymbol, ELEMENTS, shellsOf } from '../data/periodic';
import type { Language } from '../i18n';
import { useAppStore } from '../state/store';

function Panel({ children, label }: { children: ReactNode; label: string }) {
  return (
    <aside
      aria-label={label}
      className="pointer-events-auto fixed inset-x-3 bottom-3 z-10 max-h-[46vh] overflow-y-auto rounded-[20px] bg-panel p-5 ring-1 ring-rim backdrop-blur-md sm:inset-x-auto sm:bottom-auto sm:right-5 sm:top-20 sm:max-h-[calc(100vh-7rem)] sm:w-[340px]"
    >
      {children}
    </aside>
  );
}

function Row({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-white/5 py-2 first:border-t-0">
      <dt className="text-sm text-muted">{term}</dt>
      <dd className="text-right text-sm tabular-nums text-text">{children}</dd>
    </div>
  );
}

function BackButton() {
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

function ElementPanel({ symbol }: { symbol: string }) {
  const { t, i18n } = useTranslation();
  const cell = elementBySymbol(symbol);
  if (!cell) return null;
  const language = i18n.language as Language;
  return (
    <Panel label={symbol}>
      <BackButton />
      <div className="flex items-end gap-4">
        <span className="font-display text-6xl font-semibold leading-none tracking-tight">{cell.symbol}</span>
        <span className="pb-1 text-sm text-muted">{t(`category.${cell.category}`)}</span>
      </div>
      <dl className="mt-5">
        <Row term={t('element.atomicNumber')}>{cell.z}</Row>
        <Row term={t('element.period')}>{cell.period}</Row>
        <Row term={t('element.group')}>{cell.group ?? t('element.groupFBlock')}</Row>
        <Row term={t('element.block')}>{cell.block}</Row>
        <Row term={t('element.shells')}>{shellsOf(cell.z).join(', ')}</Row>
        <Row term={t('element.configuration')}>{condensedConfiguration(cell.z)}</Row>
      </dl>
      <h2 className="mt-6 text-sm font-semibold text-text">{t('element.examples')}</h2>
      <ul className="mt-2 flex flex-wrap gap-2">
        {DEMO_COMPOUNDS.map((compound) => (
          <li key={compound.id}>
            <Link
              to={`/c/${compound.id}`}
              className="inline-flex items-baseline gap-2 rounded-full px-3 py-1.5 text-sm ring-1 ring-rim transition-colors hover:bg-white/5"
            >
              <span className="font-display font-medium">{compound.formula}</span>
              <span className="text-muted">{compound.names[language] ?? compound.names.en}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function CompoundPanel({ id }: { id: string }) {
  const { t, i18n } = useTranslation();
  const compound = demoCompound(id);
  if (!compound) {
    return (
      <Panel label={id}>
        <BackButton />
        <p className="text-sm text-muted">{t('compound.notFound')}</p>
      </Panel>
    );
  }
  const language = i18n.language as Language;
  const { structure } = compound;
  const counts = new Map<string, number>();
  for (const atom of structure.atoms) counts.set(atom.el, (counts.get(atom.el) ?? 0) + 1);
  return (
    <Panel label={compound.formula}>
      <BackButton />
      <p className="font-display text-4xl font-semibold leading-none tracking-tight">{compound.formula}</p>
      <p className="mt-2 text-lg">{compound.names[language] ?? compound.names.en}</p>
      <p className="mt-1 text-sm text-muted">{t(`compound.${structure.kind}`)}</p>
      {structure.kind === 'molecule' && (
        <dl className="mt-5">
          {[...counts.entries()].map(([symbol, count]) => (
            <Row key={symbol} term={symbol}>
              {count}
            </Row>
          ))}
        </dl>
      )}
      <p className="mt-5 text-sm text-muted">{t('hint.rotate')}</p>
    </Panel>
  );
}

function TableHint() {
  const { t } = useTranslation();
  const selection = useAppStore((state) => state.selection);
  const clearSelection = useAppStore((state) => state.clearSelection);
  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-3 z-10 flex flex-col items-start gap-2 sm:left-5 sm:right-auto sm:bottom-5 sm:max-w-md">
      {selection.length > 0 && (
        <div className="pointer-events-auto flex items-center gap-3 rounded-full bg-panel py-1.5 pl-4 pr-1.5 ring-1 ring-gold/40 backdrop-blur-md">
          <span className="text-sm">{t('selection.count', { count: selection.length })}</span>
          <span className="font-display text-sm font-medium text-gold">
            {selection.map((z) => ELEMENTS[z - 1]?.symbol).join(' ')}
          </span>
          <button
            type="button"
            onClick={clearSelection}
            className="rounded-full px-3 py-1 text-xs text-muted ring-1 ring-rim hover:text-text"
          >
            {t('selection.clear')}
          </button>
        </div>
      )}
      <p className="rounded-2xl bg-panel/60 px-4 py-2 text-sm text-muted backdrop-blur-sm">{t('hint.table')}</p>
    </div>
  );
}

export function InfoPanel() {
  const scene = useAppStore((state) => state.scene);
  if (scene.kind === 'element') return <ElementPanel symbol={scene.symbol} />;
  if (scene.kind === 'compound') return <CompoundPanel id={scene.id} />;
  return <TableHint />;
}
