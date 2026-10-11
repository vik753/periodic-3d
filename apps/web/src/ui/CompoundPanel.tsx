import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import type { CompoundDetail, Source } from '../data/api';
import { pickName } from '../data/api';
import type { DemoCompound } from '../data/demo';
import { demoCompound } from '../data/demo';
import { useCompound, useElements } from '../data/hooks';
import { NotFoundError } from '../data/source';
import { formatCharge, formatCount, formatNumber, formulaOrder } from './format';
import { BackButton, Panel, Row, Section, Skeleton, StatusNote } from './Panel';
import { PhotoFigure } from './PhotoFigure';

/** Wikidata classes too generic to show ("type of chemical entity", "group of isomers"…). */
const GENERIC_CLASSES = new Set([
  'Q113145171', // type of chemical entity
  'Q111360549', // type of physical object
  'Q119892838', // type of mixture of chemical entities
  'Q55640599', // group of chemical entities
  'Q15711994', // group of isomeric entities
  'Q59199015', // group of stereoisomers
  'Q47154513', // structural class of chemical entities
  'Q17339814', // group or class of chemical substances
  'Q122754124', // ambiguous Wikidata item
]);

const ROLE_KEYS: Record<Source['role'], string> = {
  identity: 'compound.roleIdentity',
  description: 'compound.roleDescription',
  properties: 'compound.roleProperties',
  structure: 'compound.roleStructure',
  photo: 'compound.rolePhoto',
};

function Composition({ compound }: { compound: CompoundDetail }) {
  const { t, i18n } = useTranslation();
  const elements = useElements();
  const bySymbol = new Map(elements.data?.elements.map((element) => [element.symbol, element] as const) ?? []);
  return (
    <Section title={t('compound.composition')}>
      <dl>
        {formulaOrder(compound.formula, compound.elements).map((symbol) => (
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
            <dd className="text-sm tabular-nums">× {formatCount(compound.composition[symbol] ?? 0, i18n.language)}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

function Sources({ sources }: { sources: Source[] }) {
  const { t } = useTranslation();
  return (
    <Section title={t('compound.sources')}>
      <ul className="space-y-1.5 text-xs leading-relaxed text-muted">
        {sources.map((source) => (
          <li key={`${source.role}-${source.name}`}>
            <span className="text-text/80">{t(ROLE_KEYS[source.role])}: </span>
            {source.url ? (
              <a href={source.url} target="_blank" rel="noreferrer" className="underline decoration-rim underline-offset-2 hover:text-text">
                {source.name}
              </a>
            ) : (
              source.name
            )}
            <span>, {source.license}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function RealCompound({ compound }: { compound: CompoundDetail }) {
  const { t, i18n } = useTranslation();
  const language = i18n.language;
  const name = pickName(compound.names, language);
  const localDescription = compound.descriptions[language as 'en' | 'ru' | 'uk'];
  const description = localDescription ?? compound.descriptions.en;
  const classes = compound.classes.filter((item) => !GENERIC_CLASSES.has(item.qid) && Object.keys(item.names).length > 0);
  const kind = compound.structureInfo?.kind;

  return (
    <Panel label={`${compound.formula} ${name}`}>
      <BackButton />
      <p className="font-display text-4xl font-semibold leading-none tracking-tight">{compound.formula}</p>
      {name && <h1 className="mt-3 text-xl font-medium leading-snug">{name}</h1>}
      <p className="mt-1 text-sm text-muted">{kind ? t(`compound.${kind}`) : t('compound.noStructure')}</p>

      {description && (
        <div className="mt-4">
          <p className="text-sm leading-relaxed text-text/90">{description}</p>
          {!localDescription && t('compound.englishDescription') && (
            <p className="mt-1 text-xs text-muted">{t('compound.englishDescription')}</p>
          )}
        </div>
      )}

      {compound.photo && <PhotoFigure photo={compound.photo} alt={name || compound.formula} />}

      <Composition compound={compound} />

      <dl className="mt-4">
        {compound.mass != null && (
          <Row term={t('compound.mass')}>
            {formatNumber(compound.mass, language, 3)} {t('compound.unitMass')}
          </Row>
        )}
        {compound.charge !== 0 && <Row term={t('compound.charge')}>{formatCharge(compound.charge)}</Row>}
      </dl>
      {compound.iupac && !compound.iupac.includes(';') && (
        <p className="mt-2 break-words text-xs text-muted">
          {t('compound.iupac')}: <span className="text-text/80">{compound.iupac}</span>
        </p>
      )}

      {classes.length > 0 && (
        <Section title={t('compound.classes')}>
          <ul className="flex flex-wrap gap-1.5">
            {classes.map((item) => (
              <li key={item.qid} className="rounded-full px-2.5 py-1 text-xs ring-1 ring-rim">
                {pickName(item.names, language)}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {compound.similar && compound.similar.length > 0 && (
        <Section title={t('compound.similar')}>
          <ul className="flex flex-col">
            {compound.similar.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/c/${item.id}`}
                  className="-mx-2 flex items-baseline gap-3 rounded-xl px-2 py-1.5 transition-colors hover:bg-white/5"
                >
                  <span className="min-w-[4.5rem] font-display text-sm font-medium">{item.formula}</span>
                  <span className="truncate text-sm text-muted">{pickName(item.names, language)}</span>
                </Link>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs leading-relaxed text-muted">{t('compound.similarHint')}</p>
        </Section>
      )}

      {compound.structure && <p className="mt-5 text-sm text-muted">{t('hint.rotate')}</p>}
      <Sources sources={compound.sources} />
    </Panel>
  );
}

function DemoCompoundPanel({ compound }: { compound: DemoCompound }) {
  const { t, i18n } = useTranslation();
  const { structure } = compound;
  const counts = new Map<string, number>();
  for (const atom of structure.atoms) counts.set(atom.el, (counts.get(atom.el) ?? 0) + 1);
  return (
    <Panel label={compound.formula}>
      <BackButton />
      <p className="font-display text-4xl font-semibold leading-none tracking-tight">{compound.formula}</p>
      <h1 className="mt-3 text-xl font-medium">{pickName(compound.names, i18n.language)}</h1>
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
      <StatusNote>{t('status.demo')}</StatusNote>
    </Panel>
  );
}

export function CompoundPanel({ id }: { id: string }) {
  const { t } = useTranslation();
  const demo = demoCompound(id);
  const compound = useCompound(demo ? null : id);
  if (demo) return <DemoCompoundPanel compound={demo} />;
  if (compound.data) return <RealCompound compound={compound.data} />;
  const missing = compound.unavailable || compound.error instanceof NotFoundError;
  return (
    <Panel label={id}>
      <BackButton />
      {compound.isPending ? (
        <Skeleton lines={5} />
      ) : (
        <p className="text-sm text-muted">{missing ? t('compound.notFound') : t('status.error')}</p>
      )}
    </Panel>
  );
}
