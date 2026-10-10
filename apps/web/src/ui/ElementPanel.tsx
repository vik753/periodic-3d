import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';

import type { CompoundSummary, ElementDetail, Partner } from '../data/api';
import { pickName } from '../data/api';
import { DEMO_COMPOUNDS } from '../data/demo';
import { useElement, usePair } from '../data/hooks';
import type { ElementCell } from '../data/periodic';
import { condensedConfiguration, elementBySymbol, shellsOf } from '../data/periodic';
import { pairPath } from '../data/source';
import { useAppStore } from '../state/store';
import { formatNumber } from './format';
import { BackButton, Panel, Row, Section, Skeleton, StatusNote } from './Panel';

const PARTNERS_SHOWN = 18;

function useStateLabel() {
  const { t } = useTranslation();
  return (state: string | null): string | null => {
    if (!state) return null;
    const lower = state.toLowerCase();
    const base = lower.includes('solid')
      ? t('element.stateSolid')
      : lower.includes('liquid')
        ? t('element.stateLiquid')
        : lower.includes('gas')
          ? t('element.stateGas')
          : state;
    return lower.startsWith('expected') ? t('element.stateExpected', { state: base }) : base;
  };
}

function CompoundLinks({ compounds }: { compounds: CompoundSummary[] }) {
  const { i18n } = useTranslation();
  return (
    <ul className="flex flex-col">
      {compounds.map((compound) => (
        <li key={compound.id}>
          <Link
            to={`/c/${compound.id}`}
            className="-mx-2 flex items-baseline gap-3 rounded-xl px-2 py-1.5 transition-colors hover:bg-white/5"
          >
            <span className="min-w-[4.5rem] font-display text-sm font-medium">{compound.formula}</span>
            <span className="truncate text-sm text-muted">{pickName(compound.names, i18n.language)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function Partners({ element, partners }: { element: ElementCell; partners: Partner[] }) {
  const { t } = useTranslation();
  const hoveredPartner = useAppStore((state) => state.hoveredPartner);
  const setHoveredPartner = useAppStore((state) => state.setHoveredPartner);
  return (
    <Section title={t('element.partners')}>
      <ul className="flex flex-wrap gap-1.5" onMouseLeave={() => setHoveredPartner(null)}>
        {partners.slice(0, PARTNERS_SHOWN).map((partner) => (
          <li key={partner.z}>
            <Link
              to={`/e/${element.symbol}/${partner.symbol}`}
              onMouseEnter={() => setHoveredPartner(partner.z)}
              onFocus={() => setHoveredPartner(partner.z)}
              onBlur={() => setHoveredPartner(null)}
              className={`inline-flex items-baseline gap-1.5 rounded-full px-2.5 py-1 text-sm ring-1 transition-colors ${
                hoveredPartner === partner.z ? 'bg-ray/15 ring-ray/60' : 'ring-rim hover:bg-white/5'
              }`}
            >
              <span className="font-display font-medium">{partner.symbol}</span>
              <span className="text-xs tabular-nums text-muted">{partner.count}</span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-muted">{t('rays.hint')}</p>
    </Section>
  );
}

/** Walking along one ray: the compounds of the pair, the one in focus is marked. */
export function WalkPanel({ element, partner }: { element: ElementCell; partner: ElementCell }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const pair = usePair(pairPath(element, partner));
  const walkIndex = useAppStore((state) => state.walkIndex);
  const setWalkIndex = useAppStore((state) => state.setWalkIndex);
  const listRef = useRef<HTMLOListElement>(null);
  const compounds = pair.data?.compounds ?? [];

  useEffect(() => {
    const item = listRef.current?.children[walkIndex] as HTMLElement | undefined;
    item?.scrollIntoView({ block: 'nearest' });
  }, [walkIndex]);

  return (
    <Panel label={t('rays.walkTitle', { a: element.symbol, b: partner.symbol })}>
      <button
        type="button"
        onClick={() => navigate(`/e/${element.symbol}`)}
        className="mb-4 rounded-full px-3 py-1 text-sm text-muted ring-1 ring-rim transition-colors hover:text-text"
      >
        {t('rays.back', { symbol: element.symbol })}
      </button>
      <p className="font-display text-4xl font-semibold leading-none tracking-tight">
        {element.symbol}
        <span className="mx-2 text-ray">—</span>
        {partner.symbol}
      </p>
      <h1 className="mt-3 text-lg font-medium">{t('rays.walkTitle', { a: element.symbol, b: partner.symbol })}</h1>
      {pair.data && <p className="mt-1 text-sm text-muted">{t('rays.compounds', { count: pair.data.count })}</p>}
      <p className="mt-3 text-xs leading-relaxed text-muted">{t('rays.walkHint')}</p>
      {pair.isPending && <Skeleton lines={5} />}
      {pair.isError && <StatusNote>{t('status.error')}</StatusNote>}
      <ol ref={listRef} className="mt-4 flex flex-col">
        {compounds.map((compound, index) => (
          <li key={compound.id}>
            <button
              type="button"
              onClick={() => (index === walkIndex ? navigate(`/c/${compound.id}`) : setWalkIndex(index))}
              aria-current={index === walkIndex ? 'true' : undefined}
              className={`-mx-2 flex w-[calc(100%+1rem)] items-baseline gap-3 rounded-xl px-2 py-1.5 text-left transition-colors ${
                index === walkIndex ? 'bg-ray/12 ring-1 ring-ray/50' : 'hover:bg-white/5'
              }`}
            >
              <span className="w-6 shrink-0 text-right text-xs tabular-nums text-muted">{index + 1}</span>
              <span className="min-w-[4.5rem] font-display text-sm font-medium">{compound.formula}</span>
              <span className="truncate text-sm text-muted">{pickName(compound.names, i18n.language)}</span>
            </button>
          </li>
        ))}
      </ol>
      {compounds[walkIndex] && (
        <Link
          to={`/c/${compounds[walkIndex].id}`}
          className="mt-4 inline-flex rounded-full bg-text px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-gold"
        >
          {t('rays.open')}: {compounds[walkIndex].formula}
        </Link>
      )}
    </Panel>
  );
}

function ElementFacts({ cell, data }: { cell: ElementCell; data: ElementDetail | undefined }) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const stateLabel = useStateLabel();
  const state = stateLabel(data?.standardState ?? null);
  const year = data?.yearDiscovered;
  return (
    <dl className="mt-4">
      {data?.mass != null && <Row term={t('element.mass')}>{formatNumber(data.mass, language, 4)}</Row>}
      <Row term={t('element.period')}>{cell.period}</Row>
      <Row term={t('element.group')}>{cell.group ?? t('element.groupFBlock')}</Row>
      <Row term={t('element.block')}>{cell.block}</Row>
      <Row term={t('element.configuration')}>{condensedConfiguration(cell.z)}</Row>
      <Row term={t('element.shells')}>{shellsOf(cell.z).join(', ')}</Row>
      {data?.electronegativity != null && (
        <Row term={t('element.electronegativity')}>{formatNumber(data.electronegativity, language, 2)}</Row>
      )}
      {state && <Row term={t('element.state')}>{state}</Row>}
      {data?.meltingPoint != null && (
        <Row term={t('element.meltingPoint')}>
          {formatNumber(data.meltingPoint, language, 1)} {t('element.unitKelvin')}
        </Row>
      )}
      {data?.boilingPoint != null && (
        <Row term={t('element.boilingPoint')}>
          {formatNumber(data.boilingPoint, language, 1)} {t('element.unitKelvin')}
        </Row>
      )}
      {data?.density != null && (
        <Row term={t('element.density')}>
          {formatNumber(data.density, language, 4)} {t('element.unitDensity')}
        </Row>
      )}
      {year && (
        <Row term={t('element.discovered')}>{year.toLowerCase() === 'ancient' ? t('element.ancient') : year}</Row>
      )}
    </dl>
  );
}

export function ElementPanel({ symbol, partner }: { symbol: string; partner?: string }) {
  const { t, i18n } = useTranslation();
  const cell = elementBySymbol(symbol);
  const partnerCell = partner ? elementBySymbol(partner) : undefined;
  const detail = useElement(cell ? cell.symbol : null);
  if (!cell) return null;
  if (partnerCell) return <WalkPanel element={cell} partner={partnerCell} />;
  const data = detail.data;
  const language = i18n.language;
  const name = data ? pickName(data.names, language) : '';
  const latin = data?.names.la;

  return (
    <Panel label={name || cell.symbol}>
      <BackButton />
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-display text-6xl font-semibold leading-none tracking-tight">{cell.symbol}</p>
          {name && <h1 className="mt-3 text-2xl font-medium leading-tight">{name}</h1>}
          {latin && latin !== name && <p className="mt-0.5 text-sm italic text-muted">{latin}</p>}
        </div>
        <span className="font-display text-2xl tabular-nums text-muted">{cell.z}</span>
      </header>
      <p className="mt-3 text-sm text-muted">
        {t(`category.${cell.category}`)}
        {data && data.compoundCount > 0 && (
          <>
            <br />
            {t('element.compoundCount', { count: data.compoundCount })}
          </>
        )}
      </p>

      <ElementFacts cell={cell} data={data} />

      {detail.isPending && <Skeleton lines={3} />}

      {data?.substance && (
        <Section title={t('element.substance')}>
          <p className="text-sm">
            {pickName(data.substance.names, language, pickName(data.names, language))}
            <span className="text-muted"> — {t(`compound.${data.substance.info.kind}`).toLowerCase()}</span>
          </p>
        </Section>
      )}

      {data && data.partners.length > 0 && <Partners element={cell} partners={data.partners} />}

      {data && data.topCompounds.length > 0 && (
        <Section title={t('element.compounds')}>
          <CompoundLinks compounds={data.topCompounds} />
        </Section>
      )}
      {data && data.topCompounds.length === 0 && <StatusNote>{t('element.noCompounds')}</StatusNote>}

      {detail.unavailable && (
        <>
          <Section title={t('element.examples')}>
            <ul className="flex flex-wrap gap-2">
              {DEMO_COMPOUNDS.map((compound) => (
                <li key={compound.id}>
                  <Link
                    to={`/c/${compound.id}`}
                    className="inline-flex items-baseline gap-2 rounded-full px-3 py-1.5 text-sm ring-1 ring-rim transition-colors hover:bg-white/5"
                  >
                    <span className="font-display font-medium">{compound.formula}</span>
                    <span className="text-muted">{pickName(compound.names, language)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Section>
          <StatusNote>{t('status.demo')}</StatusNote>
        </>
      )}
      {detail.isError && !detail.unavailable && <StatusNote>{t('status.error')}</StatusNote>}
    </Panel>
  );
}
