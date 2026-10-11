import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { pickName } from '../data/api';
import { useElements } from '../data/hooks';
import { ELEMENTS } from '../data/periodic';
import { useAppStore } from '../state/store';

/**
 * Keyboard and screen-reader way into the table: the 3D canvas cannot take focus.
 * The list is hidden until one of its links has focus, then it shows as a grid.
 */
export function ElementIndex() {
  const { t, i18n } = useTranslation();
  const scene = useAppStore((state) => state.scene);
  const elements = useElements();
  if (scene.kind !== 'table') return null;
  const names = new Map(elements.data?.elements.map((element) => [element.z, element.names] as const) ?? []);
  return (
    <nav
      aria-label={t('a11y.elements')}
      className="sr-only focus-within:not-sr-only focus-within:fixed focus-within:left-3 focus-within:top-20 focus-within:z-30 focus-within:max-h-[70vh] focus-within:w-[min(34rem,calc(100vw-1.5rem))] focus-within:overflow-y-auto focus-within:rounded-[20px] focus-within:bg-panel focus-within:p-4 focus-within:ring-1 focus-within:ring-rim focus-within:backdrop-blur-md"
    >
      <p className="mb-3 text-xs text-muted">{t('a11y.elementsHint')}</p>
      <ul className="grid grid-cols-6 gap-1 sm:grid-cols-9">
        {ELEMENTS.map((element) => {
          const name = pickName(names.get(element.z), i18n.language);
          return (
            <li key={element.z}>
              <Link
                to={`/e/${element.symbol}`}
                aria-label={name ? `${element.symbol}, ${name}` : element.symbol}
                className="block rounded-lg py-1 text-center font-display text-sm ring-1 ring-rim hover:bg-white/5"
              >
                {element.symbol}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
