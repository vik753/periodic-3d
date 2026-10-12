import { useId, useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { UseShares, UseSphereId, UseSource, UseTerm, Uses } from '../data/api';
import { pickName } from '../data/api';
import { formatNumber } from './format';
import { Section } from './Panel';

/** Small line icons for the ten spheres (24 × 24, stroked). */
const SPHERE_ICONS: Record<UseSphereId, string> = {
  industry: 'M3 21V10l5 3v-3l5 3V7l8 4v10H3zM7 17h2M12 17h2M17 17h1',
  materials: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM4 7.5l8 4.5 8-4.5M12 12v9',
  energy: 'M13 2L4 14h7l-1 8 9-12h-7l1-8z',
  electronics: 'M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4',
  medicine: 'M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z',
  agriculture: 'M12 21v-9m0 0C12 7 8.5 4 4 4c0 5 3.5 8 8 8zm0 0c0-4.5 3-7.5 8-7.5 0 4.5-3 7.5-8 7.5z',
  food: 'M7 3v8a2 2 0 002 2v8M5 3v5m4-5v5M17 3c-2 1-3 4-3 7h3v11',
  household: 'M3 11l9-7 9 7M5 9.5V21h5v-6h4v6h5V9.5',
  science: 'M9 3h6M10 3v6l-5.6 9.4A1.7 1.7 0 005.9 21h12.2a1.7 1.7 0 001.5-2.6L14 9V3M7.5 15h9',
  defense: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z',
};

/** Segment colours of a share bar; the last item "other" is grey. */
const SHARE_COLOURS = ['#62d2ff', '#b69cff', '#ffc857', '#7ee0b5', '#ff8fa3', '#8fa8ff', '#f5a65b', '#9be3ef'];
const OTHER_COLOUR = 'rgb(233 238 248 / 0.22)';

function SphereIcon({ id }: { id: UseSphereId }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 shrink-0 text-cyan">
      <path d={SPHERE_ICONS[id]} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SourceLinks({ ids, sources }: { ids: string[]; sources: Map<string, UseSource> }) {
  return (
    <>
      {ids.map((id, index) => {
        const source = sources.get(id);
        if (!source) return null;
        return (
          <span key={id}>
            {index > 0 && ', '}
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              title={`${source.name} — ${source.license}`}
              className="underline decoration-rim underline-offset-2 hover:text-text"
            >
              {source.short}
            </a>
          </span>
        );
      })}
    </>
  );
}

function isOther(names: UseShares['items'][number]['names']): boolean {
  return /^other( uses| applications)?$/i.test(names.en ?? '');
}

function SharesBlock({ block }: { block: UseShares }) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const scope =
    block.scope === 'world'
      ? t('uses.shareWorld', { year: block.year })
      : block.scope === 'us'
        ? t('uses.shareUs', { year: block.year })
        : t('uses.shareOther', { year: block.year });
  const colour = (index: number): string => {
    const item = block.items[index];
    if (!item || isOther(item.names)) return OTHER_COLOUR;
    return SHARE_COLOURS[index % SHARE_COLOURS.length] ?? OTHER_COLOUR;
  };
  const value = (share: number, more?: boolean) =>
    more ? t('uses.more', { value: formatNumber(share, language, 1) }) : `${formatNumber(share, language, 1)}%`;
  const List = block.ranked ? 'ol' : 'ul';
  return (
    <figure className="mb-4 rounded-2xl bg-white/[0.03] p-3 ring-1 ring-rim">
      <figcaption className="flex items-baseline justify-between gap-3 text-xs">
        <span className="font-medium text-text">{pickName(block.commodity, language)}</span>
        <span className="text-right text-muted">{scope}</span>
      </figcaption>
      {!block.ranked && (
        <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-white/[0.06]" aria-hidden="true">
          {block.items.map((item, index) =>
            item.share ? (
              <span key={index} style={{ width: `${item.share}%`, background: colour(index) }} className="h-full" />
            ) : null,
          )}
        </div>
      )}
      {block.ranked && <p className="mt-1 text-[11px] text-muted">{t('uses.ranked')}</p>}
      <List className={`mt-2 space-y-1 text-xs ${block.ranked ? 'list-inside list-decimal marker:text-muted' : ''}`}>
        {block.items.map((item, index) => (
          <li key={index} className={block.ranked ? 'text-text/90' : 'flex items-baseline gap-2'}>
            {!block.ranked && (
              <span className="h-2 w-2 shrink-0 translate-y-[1px] rounded-sm" style={{ background: colour(index) }} />
            )}
            <span className={block.ranked ? '' : 'min-w-0 flex-1 text-text/90'}>{pickName(item.names, language)}</span>
            {item.share != null && <span className="tabular-nums text-muted">{value(item.share, item.more)}</span>}
          </li>
        ))}
      </List>
      {block.group && <p className="mt-2 text-[11px] leading-snug text-muted">{t('uses.group')}</p>}
      <details className="mt-2 text-[11px] leading-snug">
        <summary className="cursor-pointer text-muted hover:text-text">{t('uses.quote')}</summary>
        <blockquote className="mt-1.5 border-l-2 border-rim pl-2 text-text/80">
          “{block.quote}”{' '}
          <a href={block.url} target="_blank" rel="noreferrer" className="whitespace-nowrap text-muted underline decoration-rim underline-offset-2 hover:text-text">
            USGS, {block.edition}
          </a>
        </blockquote>
      </details>
    </figure>
  );
}

function TermChip({
  term,
  open,
  controls,
  onToggle,
}: {
  term: UseTerm;
  open: boolean;
  controls: string;
  onToggle: () => void;
}) {
  const { t, i18n } = useTranslation();
  const name = pickName(term.names, i18n.language);
  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={controls}
        aria-label={t('uses.showSources', { name })}
        onClick={onToggle}
        className={`rounded-full px-2.5 py-1 text-left text-xs ring-1 transition-colors hover:bg-white/5 ${
          open ? 'bg-white/[0.06] ring-cyan/60' : 'ring-rim'
        }`}
      >
        {name}
        {term.share != null && <span className="ml-1.5 tabular-nums text-cyan">{formatNumber(term.share, i18n.language, 1)}%</span>}
        {term.notes?.includes('eu_not_approved') && (
          <span className="ml-1.5 inline-block h-1.5 w-1.5 -translate-y-px rounded-full bg-gold" aria-hidden="true" />
        )}
      </button>
    </li>
  );
}

/** "Where it is used": spheres with terms, USGS shares, quotes and sources (task U.4). */
export function UsesSection({ uses }: { uses: Uses }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState<string | null>(null);
  const baseId = useId();
  const sources = new Map(uses.sources.map((source) => [source.id, source] as const));

  return (
    <Section title={t('uses.title')}>
      {uses.shares?.map((block) => <SharesBlock key={block.url + pickName(block.commodity, 'en')} block={block} />)}
      <ul className="space-y-3">
        {uses.spheres.map((sphere) => {
          const selected = sphere.terms.find((term) => open === `${sphere.id}:${term.id}`);
          const detailsId = `${baseId}-${sphere.id}`;
          return (
            <li key={sphere.id}>
              <p className="flex items-center gap-2 text-xs font-medium text-text/85">
                <SphereIcon id={sphere.id} />
                {t(`uses.sphere.${sphere.id}`)}
              </p>
              <ul className="mt-1.5 flex flex-wrap gap-1.5">
                {sphere.terms.map((term) => {
                  const key = `${sphere.id}:${term.id}`;
                  return (
                    <TermChip
                      key={term.id}
                      term={term}
                      open={open === key}
                      controls={detailsId}
                      onToggle={() => setOpen(open === key ? null : key)}
                    />
                  );
                })}
              </ul>
              <div id={detailsId} aria-live="polite">
                {selected && (
                  <p className="mt-1.5 text-[11px] leading-snug text-muted">
                    {pickName(selected.names, i18n.language)} — {t('uses.sourcesOf').toLowerCase()}:{' '}
                    <SourceLinks ids={selected.sources} sources={sources} />.
                    {selected.notes?.includes('eu_not_approved') && <span className="text-gold"> {t('uses.euNotApproved')}</span>}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      {uses.quotes && uses.quotes.length > 0 && (
        <details className="mt-3 text-[11px] leading-snug">
          <summary className="cursor-pointer text-muted hover:text-text">{t('uses.quotes')}</summary>
          {uses.quotes.map((quote) => {
            const source = sources.get(quote.source);
            return (
              <blockquote key={quote.text} className="mt-1.5 border-l-2 border-rim pl-2 text-text/80">
                “{quote.text}”{' '}
                {source && (
                  <a href={source.url} target="_blank" rel="noreferrer" className="text-muted underline decoration-rim underline-offset-2 hover:text-text">
                    {source.short}
                  </a>
                )}
              </blockquote>
            );
          })}
        </details>
      )}
      <p className="mt-3 text-[11px] leading-snug text-muted">
        {t('uses.sourcesOf')}: <SourceLinks ids={uses.sources.map((source) => source.id)} sources={sources} />.{' '}
        {t('uses.hint')}
      </p>
    </Section>
  );
}
