import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { pickName } from '../data/api';
import { demoCompound } from '../data/demo';
import { useCompound, useElements, useMaterial } from '../data/hooks';
import type { Language } from '../i18n';
import { LANGUAGES, saveLanguage } from '../i18n';
import { wasAboutSeen } from '../lib/visits';
import { useAppStore } from '../state/store';
import { Search } from './Search';

const LANGUAGE_LABELS: Record<Language, string> = { uk: 'UA', ru: 'RU', en: 'EN' };

/** The periodic table's own silhouette: H and He on top, the s and p blocks, the full rows below. */
function TableIcon() {
  return (
    <svg viewBox="0 0 16 12" width="16" height="12" aria-hidden="true" fill="currentColor" className="shrink-0">
      <rect x="0" y="0" width="2.6" height="2.6" rx="0.5" />
      <rect x="13.4" y="0" width="2.6" height="2.6" rx="0.5" />
      <rect x="0" y="3.2" width="5.4" height="2.6" rx="0.5" />
      <rect x="9.2" y="3.2" width="6.8" height="2.6" rx="0.5" />
      <rect x="0" y="6.4" width="16" height="5.6" rx="0.5" />
    </svg>
  );
}

export function TopBar() {
  const { t, i18n } = useTranslation();
  const scene = useAppStore((state) => state.scene);
  const pagePanel = useAppStore((state) => state.pagePanel);
  const awayFromTable = scene.kind !== 'table' || pagePanel;
  // The glow is bright until the visitor has opened the page once. Closing the page
  // flips pagePanel, so the bar renders again and reads the new value.
  const aboutSeen = wasAboutSeen();
  const elements = useElements();
  const compoundId = scene.kind === 'compound' ? scene.id : null;
  const compound = useCompound(compoundId);
  const material = useMaterial(scene.kind === 'material' ? scene.id : null);

  const crumbs: Array<{ label: string; detail?: string }> = [];
  if (scene.kind === 'element') {
    const element = elements.data?.elements.find((item) => item.symbol === scene.symbol);
    crumbs.push({ label: scene.symbol, detail: element ? pickName(element.names, i18n.language) : undefined });
  }
  if (scene.kind === 'compound') {
    crumbs.push({ label: demoCompound(scene.id)?.formula ?? compound.data?.formula ?? scene.id });
  }
  if (scene.kind === 'material') crumbs.push({ label: material.data?.formula ?? scene.id, detail: t('material.kind') });
  if (scene.kind === 'set') crumbs.push({ label: scene.symbols.join(' + ') });

  const changeLanguage = (language: Language) => {
    void i18n.changeLanguage(language);
    saveLanguage(language);
  };

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-20 flex flex-wrap items-start justify-between gap-3 p-3 sm:flex-nowrap sm:p-5">
      <nav aria-label={t('nav.breadcrumbs')} className="pointer-events-auto flex min-w-0 items-center gap-3 text-sm">
        {awayFromTable ? (
          // One click home from any depth: the camera flies back to the whole table.
          <Link
            to="/"
            title={t('nav.toTableTitle')}
            className="to-table-in flex h-8 shrink-0 items-center gap-2 rounded-full bg-panel pl-3 pr-3.5 font-medium text-text ring-1 ring-rim backdrop-blur-md transition-colors hover:text-gold hover:ring-gold/60"
          >
            <TableIcon />
            <span className="hidden sm:inline">{t('nav.toTable')}</span>
            <span className="sm:hidden">{t('nav.table')}</span>
          </Link>
        ) : (
          <Link
            to="/"
            className="font-display text-[15px] font-semibold tracking-tight text-text hover:text-gold sm:text-base"
          >
            <span className="hidden sm:inline">{t('app.title')}</span>
            <span className="sm:hidden">{t('app.short')}</span>
          </Link>
        )}
        {crumbs.map((crumb) => (
          <span key={crumb.label} className="hidden min-w-0 items-baseline gap-2 sm:flex" aria-current="page">
            <span className="font-display font-medium text-text">{crumb.label}</span>
            {crumb.detail && <span className="truncate text-muted">{crumb.detail}</span>}
          </span>
        ))}
      </nav>
      <div
        className={`order-last flex w-full justify-center sm:order-none sm:w-auto sm:flex-1 ${
          scene.kind === 'table' ? '' : 'hidden sm:flex'
        }`}
      >
        <Search />
      </div>
      <div className="pointer-events-auto flex shrink-0 items-center gap-2">
        <Link
          to="/about"
          title={t('about.open')}
          data-calm={aboutSeen}
          className="glow-button flex h-8 items-center gap-2 rounded-full bg-panel pl-1 pr-3 text-sm font-medium text-text backdrop-blur-md transition-colors hover:text-gold"
        >
          <span
            aria-hidden="true"
            className="flex h-6 w-6 items-center justify-center rounded-full bg-gold/15 font-display text-xs font-semibold text-gold"
          >
            i
          </span>
          <span className="hidden sm:inline">{t('about.button')}</span>
          <span className="sm:hidden">{t('about.buttonShort')}</span>
        </Link>
        <div
          role="group"
          aria-label={t('lang.label')}
          className="pointer-events-auto flex shrink-0 gap-0.5 rounded-full bg-panel p-1 ring-1 ring-rim backdrop-blur-md"
        >
          {LANGUAGES.map((language) => (
            <button
              key={language}
              type="button"
              onClick={() => changeLanguage(language)}
              aria-pressed={i18n.language === language}
              className={`rounded-full px-2.5 py-1 text-xs font-semibold transition-colors ${
                i18n.language === language ? 'bg-text text-ink' : 'text-muted hover:text-text'
              }`}
            >
              {LANGUAGE_LABELS[language]}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
