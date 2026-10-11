import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import type { ElementSummary } from '../data/api';
import { pickName } from '../data/api';
import { normalizeText, searchIndex, useCompoundIndex } from '../data/compoundIndex';
import { useElements } from '../data/hooks';
import { FormulaRow } from './FormulaRow';

interface Result {
  key: string;
  path: string;
  title: string;
  subtitle: string;
  kind: 'element' | 'compound' | 'material';
}

function matchElements(elements: ElementSummary[], query: string, language: string): ElementSummary[] {
  const needle = normalizeText(query);
  if (!needle) return [];
  const exact = elements.filter((element) => element.symbol.toLowerCase() === needle);
  const byName = elements.filter(
    (element) =>
      !exact.includes(element) && Object.values(element.names).some((name) => normalizeText(name ?? '').startsWith(needle)),
  );
  const local = (element: ElementSummary) => pickName(element.names, language);
  return [...exact, ...byName.sort((a, b) => local(a).localeCompare(local(b)))].slice(0, 4);
}

/** Search box: elements and compounds by symbol, formula or name in UA/RU/EN. */
export function Search() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [touched, setTouched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const elements = useElements();
  const index = useCompoundIndex(touched);

  // "/" or Ctrl+K focuses the search from anywhere.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
      if ((event.key === '/' && !typing) || (event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey))) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const results = useMemo<Result[]>(() => {
    if (!query.trim()) return [];
    const language = i18n.language;
    const found: Result[] = matchElements(elements.data?.elements ?? [], query, language).map((element) => ({
      key: `e-${element.symbol}`,
      path: `/e/${element.symbol}`,
      title: element.symbol,
      subtitle: pickName(element.names, language),
      kind: 'element',
    }));
    // A GNoME id (10 hex characters) opens the predicted material's card.
    const id = query.trim().toLowerCase();
    if (/^[0-9a-f]{10}$/.test(id)) {
      found.push({ key: `m-${id}`, path: `/m/${id}`, title: id, subtitle: t('material.kind'), kind: 'material' });
    }
    for (const entry of searchIndex(index.data ?? [], query, 10)) {
      found.push({
        key: `c-${entry.id}`,
        path: `/c/${entry.id}`,
        title: entry.formula,
        subtitle: pickName(entry.names, language),
        kind: 'compound',
      });
    }
    return found;
  }, [query, elements.data, index.data, i18n.language, t]);

  const go = (result: Result | undefined) => {
    if (!result) return;
    navigate(result.path);
    setOpen(false);
    setQuery('');
    inputRef.current?.blur();
  };

  const onKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((value) => Math.min(value + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((value) => Math.max(value - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      go(results[active]);
    } else if (event.key === 'Escape') {
      event.stopPropagation();
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  const showList = open && query.trim().length > 0;
  return (
    <div className="pointer-events-auto relative w-full max-w-[22rem]">
      <input
        ref={inputRef}
        type="search"
        value={query}
        placeholder={t('search.placeholder')}
        aria-label={t('search.label')}
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && results[active] ? `${listId}-${active}` : undefined}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => {
          setTouched(true);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        className="w-full rounded-full bg-panel px-4 py-1.5 text-sm text-text ring-1 ring-rim backdrop-blur-md placeholder:text-muted/80 focus:outline-none focus:ring-gold/70"
      />
      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute inset-x-0 top-full z-30 mt-2 max-h-[60vh] overflow-y-auto rounded-2xl bg-panel p-1.5 ring-1 ring-rim backdrop-blur-md"
        >
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm text-muted">{index.isPending && touched ? t('status.loading') : t('search.empty')}</li>
          )}
          {results.map((result, position) => (
            <li
              key={result.key}
              id={`${listId}-${position}`}
              role="option"
              aria-selected={position === active}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => setActive(position)}
              onClick={() => go(result)}
              className={`flex cursor-pointer items-baseline gap-3 rounded-xl px-3 py-1.5 ${
                position === active ? 'bg-white/10' : ''
              }`}
            >
              <FormulaRow
                formula={result.title}
                name={result.subtitle}
                formulaClassName={`font-display font-semibold ${
                  result.kind === 'element'
                    ? 'min-w-[2rem] text-gold'
                    : result.kind === 'material'
                      ? 'min-w-[4rem] text-violet'
                      : 'min-w-[4rem]'
                }`}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
