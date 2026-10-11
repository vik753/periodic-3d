import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { GnomeInfo, Material } from '../data/api';
import { pickName } from '../data/api';
import { useElements, useGnome, useMaterial } from '../data/hooks';
import { NotFoundError } from '../data/source';
import { formatCount, formatNumber, formulaOrder } from './format';
import { BackButton, Panel, Row, Section, Skeleton } from './Panel';
import { ReportLink } from './ReportLink';

/** Below this band gap (eV) the calculation describes a conductor. */
const METALLIC_GAP_EV = 0.1;

/** "Predicted, not confirmed": the violet mark of every GNoME material (ADR 0007). */
export function PredictedBadge() {
  const { t } = useTranslation();
  return (
    <p className="inline-flex items-center gap-2 rounded-full bg-violet/12 px-3 py-1 text-xs font-medium text-violet ring-1 ring-violet/40">
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-violet" />
      {t('material.badge')}
    </p>
  );
}

function Composition({ material }: { material: Material }) {
  const { t, i18n } = useTranslation();
  const elements = useElements();
  const bySymbol = new Map(elements.data?.elements.map((element) => [element.symbol, element] as const) ?? []);
  return (
    <Section title={t('compound.composition')}>
      <dl>
        {formulaOrder(material.formula, material.elements).map((symbol) => (
          <div key={symbol} className="flex items-baseline justify-between gap-4 border-t border-white/5 py-1.5 first:border-t-0">
            <dt className="flex min-w-0 items-baseline gap-2">
              <Link
                to={`/e/${symbol}`}
                className="min-w-[2.25rem] rounded-full px-2 py-0.5 text-center font-display text-sm font-medium ring-1 ring-rim hover:bg-white/5"
              >
                {symbol}
              </Link>
              <span className="truncate text-sm text-muted">{pickName(bySymbol.get(symbol)?.names, i18n.language)}</span>
            </dt>
            <dd className="text-sm tabular-nums">× {formatCount(material.composition[symbol] ?? 0, i18n.language)}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

function Energy({ value }: { value: number }) {
  const { t, i18n } = useTranslation();
  const text = formatNumber(Math.abs(value), i18n.language, 3);
  return (
    <>
      {value < 0 ? `−${text}` : text} {t('material.unitEnergy')}
    </>
  );
}

function Attribution({ gnome, id }: { gnome: GnomeInfo | null; id: string }) {
  const { t } = useTranslation();
  return (
    <Section title={t('compound.sources')}>
      <ul className="space-y-1.5 text-xs leading-relaxed text-muted">
        <li>
          <span className="text-text/80">{t('material.source')}: </span>
          <a
            href={gnome?.sourceUrl ?? 'https://github.com/google-deepmind/materials_discovery'}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-rim underline-offset-2 hover:text-text"
          >
            GNoME (Google DeepMind)
          </a>
          <span>, {t('material.id')} {id}</span>
        </li>
        <li>
          <span className="text-text/80">{t('material.licenseTitle')}: </span>
          <a
            href={gnome?.licenseUrl ?? 'https://creativecommons.org/licenses/by-nc/4.0/'}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-rim underline-offset-2 hover:text-text"
          >
            {gnome?.license ?? 'CC BY-NC 4.0'}
          </a>
          <span>. {t('material.licenseNote')}</span>
        </li>
        {gnome?.citation && (
          <li>
            <span className="text-text/80">{t('material.cite')}: </span>
            {gnome.citation}
          </li>
        )}
      </ul>
    </Section>
  );
}

function MaterialCard({ material }: { material: Material }) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const gnome = useGnome();
  const system = material.crystalSystem?.toLowerCase();
  const gap = material.bandgap;

  return (
    <Panel label={`${material.formula} ${t('material.kind')}`}>
      <BackButton />
      <p className="font-display text-4xl font-semibold leading-none tracking-tight">{material.formula}</p>
      <h1 className="mt-3 text-xl font-medium leading-snug">{t('material.kind')}</h1>
      <div className="mt-3">
        <PredictedBadge />
      </div>
      <p className="mt-4 text-sm leading-relaxed text-text/90">{t('material.intro')}</p>

      <Composition material={material} />

      <Section title={t('material.cell')}>
        <dl>
          {system && (
            <Row term={t('material.crystalSystem')}>{t(`material.system.${system}`, { defaultValue: system })}</Row>
          )}
          {material.spaceGroup && (
            <Row term={t('material.spaceGroup')}>
              {material.spaceGroup}
              {material.spaceGroupNumber != null && <span className="text-muted"> (№ {material.spaceGroupNumber})</span>}
            </Row>
          )}
          <Row term={t('material.atoms')}>{material.nsites}</Row>
          {material.volume != null && (
            <Row term={t('material.volume')}>{formatNumber(material.volume, language, 1)} Å³</Row>
          )}
          {material.density != null && (
            <Row term={t('element.density')}>
              {formatNumber(material.density, language, 2)} {t('element.unitDensity')}
            </Row>
          )}
        </dl>
      </Section>

      <Section title={t('material.calculation')}>
        <dl>
          {material.decompositionEnergy != null && (
            <Row term={t('material.decomposition')}>
              <Energy value={material.decompositionEnergy} />
            </Row>
          )}
          {material.r2scanDecompositionEnergy != null && (
            <Row term={t('material.r2scan')}>
              <Energy value={material.r2scanDecompositionEnergy} />
            </Row>
          )}
          {material.formationEnergy != null && (
            <Row term={t('material.formation')}>
              <Energy value={material.formationEnergy} />
            </Row>
          )}
          {gap != null && (
            <Row term={t('material.bandgap')}>
              {gap < METALLIC_GAP_EV ? t('material.conductor') : `${formatNumber(gap, language, 2)} ${t('material.unitEv')}`}
            </Row>
          )}
          {material.dimensionality && (
            <Row term={t('material.dimensionality')}>
              {t(`material.dim.${material.dimensionality}`, { defaultValue: material.dimensionality })}
            </Row>
          )}
        </dl>
        <p className="mt-2 text-xs leading-relaxed text-muted">{t('material.stableHint')}</p>
      </Section>

      <p className="mt-5 text-sm text-muted">{t('hint.rotate')}</p>
      <Attribution gnome={gnome} id={material.id} />
      <ReportLink kind="material" id={material.id} title={material.formula} />
    </Panel>
  );
}

export function MaterialPanel({ id }: { id: string }) {
  const { t } = useTranslation();
  const material = useMaterial(id);
  if (material.data) return <MaterialCard material={material.data} />;
  return (
    <Panel label={id}>
      <BackButton />
      <p className="font-display text-2xl font-semibold">{id}</p>
      <div className="mt-3">
        <PredictedBadge />
      </div>
      {material.isPending ? (
        <Skeleton lines={5} />
      ) : (
        <p className="mt-4 text-sm text-muted">
          {material.unavailable
            ? t('material.unavailable')
            : material.missing || material.error instanceof NotFoundError
              ? t('material.notFound')
              : t('status.error')}
        </p>
      )}
    </Panel>
  );
}
