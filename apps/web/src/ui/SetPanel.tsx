import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';

import { pickName } from '../data/api';
import { useElements } from '../data/hooks';
import { elementByZ } from '../data/periodic';
import { useAppStore } from '../state/store';
import { useCloud } from '../state/useCloud';
import { Panel, Section, Skeleton, StatusNote } from './Panel';

const LIST_LIMIT = 60;
const EXTRAS_SHOWN = 16;

/** The multi-element cloud: chosen elements, mode, other elements found, the compounds. */
export function SetPanel({ symbols }: { symbols: string[] }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const elements = useElements();
  const mode = useAppStore((state) => state.cloudMode);
  const setMode = useAppStore((state) => state.setCloudMode);
  const hover = useAppStore((state) => state.cloudHover);
  const focus = useAppStore((state) => state.cloudFocus);
  const setHover = useAppStore((state) => state.setCloudHover);
  const setFocus = useAppStore((state) => state.setCloudFocus);
  const { result, isPending, unavailable } = useCloud();
  const nameOf = (symbol: string) =>
    pickName(elements.data?.elements.find((element) => element.symbol === symbol)?.names, i18n.language);

  const extras = result
    ? [...result.extras.entries()].sort((a, b) => b[1] - a[1]).slice(0, EXTRAS_SHOWN)
    : [];
  const focused = result?.items.find((entry) => entry.id === focus);

  return (
    <Panel label={t('cloud.title')}>
      <button
        type="button"
        onClick={() => navigate('/')}
        className="mb-4 rounded-full px-3 py-1 text-sm text-muted ring-1 ring-rim transition-colors hover:text-text"
      >
        {t('cloud.back')}
      </button>
      <h1 className="text-sm text-muted">{t('cloud.title')}</h1>
      <ul className="mt-2 flex flex-wrap gap-2">
        {symbols.map((symbol) => (
          <li key={symbol} className="flex items-baseline gap-2 rounded-full bg-gold/15 px-3 py-1 ring-1 ring-gold/50">
            <span className="font-display text-lg font-semibold text-gold">{symbol}</span>
            <span className="text-sm text-text/80">{nameOf(symbol)}</span>
          </li>
        ))}
      </ul>

      <div role="radiogroup" aria-label={t('cloud.mode')} className="mt-4 inline-flex rounded-full bg-white/5 p-1 ring-1 ring-rim">
        {(['contains', 'only'] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={mode === value}
            onClick={() => setMode(value)}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              mode === value ? 'bg-text font-semibold text-ink' : 'text-muted hover:text-text'
            }`}
          >
            {t(value === 'contains' ? 'cloud.contains' : 'cloud.only')}
          </button>
        ))}
      </div>

      {isPending && <Skeleton lines={5} />}
      {unavailable && <StatusNote>{t('status.demo')}</StatusNote>}
      {result && <p className="mt-3 text-sm text-muted">{t('cloud.count', { count: result.total })}</p>}

      {focused && (
        <div className="mt-4 rounded-2xl bg-white/[0.04] p-3 ring-1 ring-cyan/40">
          <p className="font-display text-2xl font-semibold leading-tight">{focused.formula}</p>
          <p className="mt-1 text-sm">{pickName(focused.names, i18n.language)}</p>
          <div className="mt-3 flex gap-2">
            <Link
              to={`/c/${focused.id}`}
              className="rounded-full bg-text px-3 py-1.5 text-sm font-semibold text-ink transition-colors hover:bg-gold"
            >
              {t('rays.open')}
            </Link>
            <button
              type="button"
              onClick={() => setFocus(null)}
              className="rounded-full px-3 py-1.5 text-sm text-muted ring-1 ring-rim hover:text-text"
            >
              {t('cloud.overview')}
            </button>
          </div>
        </div>
      )}

      {extras.length > 0 && mode === 'contains' && (
        <Section title={t('cloud.extras')}>
          <ul className="flex flex-wrap gap-1.5">
            {extras.map(([z, count]) => {
              const cell = elementByZ(z);
              if (!cell) return null;
              return (
                <li key={z}>
                  <Link
                    to={`/set/${[...symbols, cell.symbol].join('-')}`}
                    title={t('cloud.addElement', { symbol: cell.symbol })}
                    className="inline-flex items-baseline gap-1.5 rounded-full px-2.5 py-1 text-sm ring-1 ring-cyan/40 transition-colors hover:bg-cyan/10"
                  >
                    <span className="font-display font-medium text-cyan">{cell.symbol}</span>
                    <span className="text-xs tabular-nums text-muted">{count}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-xs text-muted">{t('cloud.extrasHint')}</p>
        </Section>
      )}

      {result && result.items.length > 0 && (
        <Section title={t('cloud.list')}>
          <ol className="flex flex-col" onMouseLeave={() => setHover(null)}>
            {result.items.slice(0, LIST_LIMIT).map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  onMouseEnter={() => setHover(entry.id)}
                  onFocus={() => setHover(entry.id)}
                  onClick={() => (entry.id === focus ? navigate(`/c/${entry.id}`) : setFocus(entry.id))}
                  aria-current={entry.id === focus ? 'true' : undefined}
                  className={`-mx-2 flex w-[calc(100%+1rem)] items-baseline gap-3 rounded-xl px-2 py-1.5 text-left transition-colors ${
                    entry.id === focus ? 'bg-cyan/10 ring-1 ring-cyan/50' : entry.id === hover ? 'bg-white/5' : 'hover:bg-white/5'
                  }`}
                >
                  <span className="min-w-[4.5rem] font-display text-sm font-medium">{entry.formula}</span>
                  <span className="truncate text-sm text-muted">{pickName(entry.names, i18n.language)}</span>
                </button>
              </li>
            ))}
          </ol>
        </Section>
      )}
      {result && result.total === 0 && <StatusNote>{t('cloud.empty')}</StatusNote>}
    </Panel>
  );
}
