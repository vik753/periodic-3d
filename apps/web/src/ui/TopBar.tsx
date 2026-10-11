import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { pickName } from '../data/api';
import { demoCompound } from '../data/demo';
import { useCompound, useElements } from '../data/hooks';
import type { Language } from '../i18n';
import { LANGUAGES, saveLanguage } from '../i18n';
import { useAppStore } from '../state/store';
import { Search } from './Search';

const LANGUAGE_LABELS: Record<Language, string> = { uk: 'UA', ru: 'RU', en: 'EN' };

export function TopBar() {
  const { t, i18n } = useTranslation();
  const scene = useAppStore((state) => state.scene);
  const elements = useElements();
  const compoundId = scene.kind === 'compound' ? scene.id : null;
  const compound = useCompound(compoundId);

  const crumbs: Array<{ label: string; detail?: string }> = [];
  if (scene.kind === 'element') {
    const element = elements.data?.elements.find((item) => item.symbol === scene.symbol);
    crumbs.push({ label: scene.symbol, detail: element ? pickName(element.names, i18n.language) : undefined });
  }
  if (scene.kind === 'compound') {
    crumbs.push({ label: demoCompound(scene.id)?.formula ?? compound.data?.formula ?? scene.id });
  }
  if (scene.kind === 'set') crumbs.push({ label: scene.symbols.join(' + ') });

  const changeLanguage = (language: Language) => {
    void i18n.changeLanguage(language);
    saveLanguage(language);
  };

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-20 flex flex-wrap items-start justify-between gap-3 p-3 sm:flex-nowrap sm:p-5">
      <nav aria-label={t('nav.breadcrumbs')} className="pointer-events-auto flex min-w-0 items-baseline gap-2 text-sm">
        <Link
          to="/"
          className="font-display text-[15px] font-semibold tracking-tight text-text hover:text-gold sm:text-base"
        >
          <span className="hidden sm:inline">{t('app.title')}</span>
          <span className="sm:hidden">{t('app.short')}</span>
        </Link>
        {crumbs.map((crumb) => (
          <span key={crumb.label} className="flex items-baseline gap-2 text-muted">
            <span aria-hidden="true">/</span>
            <span className="font-display font-medium text-text" aria-current="page">
              {crumb.label}
            </span>
            {crumb.detail && <span className="hidden truncate text-muted sm:inline">{crumb.detail}</span>}
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
          aria-label={t('about.open')}
          title={t('about.open')}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-panel font-display text-sm font-semibold text-muted ring-1 ring-rim backdrop-blur-md transition-colors hover:text-text"
        >
          i
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
