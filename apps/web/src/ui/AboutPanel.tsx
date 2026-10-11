import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { useMeta } from '../data/hooks';
import { markAboutSeen } from '../lib/visits';
import { useAppStore } from '../state/store';
import { formatCount } from './format';
import { GuideVideoButton } from './GuideVideo';
import { BackButton, Panel, Row, Section } from './Panel';

const REPOSITORY_URL = 'https://github.com/vik753/periodic-3d';

/** Data sources in the order a visitor meets them; licenses as the sources state them. */
const SOURCES = [
  { name: 'Wikidata', url: 'https://www.wikidata.org', license: 'CC0', role: 'about.srcWikidata' },
  { name: 'Wikipedia', url: 'https://www.wikipedia.org', license: 'CC BY-SA 4.0', role: 'about.srcWikipedia' },
  {
    name: 'PubChem',
    url: 'https://pubchem.ncbi.nlm.nih.gov',
    license: 'public domain (NIH)',
    role: 'about.srcPubchem',
  },
  { name: 'Materials Project', url: 'https://materialsproject.org', license: 'CC BY 4.0', role: 'about.srcMaterials' },
  { name: 'RDKit', url: 'https://www.rdkit.org', license: 'BSD-3-Clause', role: 'about.srcRdkit' },
  {
    name: 'Wikimedia Commons',
    url: 'https://commons.wikimedia.org',
    license: 'CC BY-SA, CC BY, CC0',
    role: 'about.srcCommons',
  },
  {
    name: 'GNoME (Google DeepMind)',
    url: 'https://github.com/google-deepmind/materials_discovery',
    license: 'CC BY-NC 4.0',
    role: 'about.srcGnome',
  },
] as const;

const HOW_TO = ['about.how1', 'about.how2', 'about.how3', 'about.how4', 'about.how5'] as const;

export function AboutPanel() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const meta = useMeta();
  const language = i18n.language;

  const setPagePanel = useAppStore((state) => state.setPagePanel);
  useEffect(() => {
    setPagePanel(true);
    markAboutSeen();
    return () => setPagePanel(false);
  }, [setPagePanel]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') navigate('/');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate]);

  const counts = meta.data?.counts ?? {};
  const created = meta.data ? new Date(meta.data.created) : null;

  return (
    <Panel label={t('about.title')}>
      <BackButton />
      <h1 className="font-display text-2xl font-semibold leading-tight tracking-tight">{t('about.title')}</h1>
      <p className="mt-3 text-sm leading-relaxed text-text/90">{t('about.intro')}</p>
      <GuideVideoButton />

      <Section title={t('about.howTitle')}>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-text/90 marker:text-muted">
          {HOW_TO.map((key) => (
            <li key={key}>{t(key)}</li>
          ))}
        </ul>
      </Section>

      {meta.data && (
        <Section title={t('about.dataTitle')}>
          <dl>
            <Row term={t('about.version')}>{meta.data.version}</Row>
            {counts.compounds != null && (
              <Row term={t('about.compounds')}>{formatCount(counts.compounds, language)}</Row>
            )}
            {counts.structures != null && (
              <Row term={t('about.structures')}>{formatCount(counts.structures, language)}</Row>
            )}
            {counts.pairs != null && <Row term={t('about.pairs')}>{formatCount(counts.pairs, language)}</Row>}
            {meta.data.gnome?.counts.materials != null && (
              <Row term={t('about.predicted')}>{formatCount(meta.data.gnome.counts.materials, language)}</Row>
            )}
            {created && !Number.isNaN(created.getTime()) && (
              <Row term={t('about.built')}>{created.toLocaleDateString(language)}</Row>
            )}
          </dl>
        </Section>
      )}

      <Section title={t('about.sourcesTitle')}>
        <ul className="space-y-2 text-sm leading-relaxed">
          {SOURCES.map((source) => (
            <li key={source.name}>
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="font-medium underline decoration-rim underline-offset-2 hover:text-gold"
              >
                {source.name}
              </a>
              <span className="text-muted">
                {' '}
                — {t(source.role)}. {source.license}.
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs leading-relaxed text-muted">{t('about.perRecord')}</p>
        <p className="mt-1 text-xs leading-relaxed text-muted">{t('about.gnome')}</p>
        {meta.data?.gnome?.citation && (
          <p className="mt-1 text-xs leading-relaxed text-muted">
            {t('about.cite')}: {meta.data.gnome.citation}
          </p>
        )}
      </Section>

      <Section title={t('about.codeTitle')}>
        <p className="text-sm leading-relaxed text-text/90">
          {t('about.code')}{' '}
          <a
            href={REPOSITORY_URL}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-rim underline-offset-2 hover:text-gold"
          >
            github.com/vik753/periodic-3d
          </a>
        </p>
      </Section>
    </Panel>
  );
}
