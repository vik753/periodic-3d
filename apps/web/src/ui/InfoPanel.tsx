import { useTranslation } from 'react-i18next';

import { ELEMENTS } from '../data/periodic';
import { useAppStore } from '../state/store';
import { CompoundPanel } from './CompoundPanel';
import { ElementPanel } from './ElementPanel';

function TableHint() {
  const { t } = useTranslation();
  const selection = useAppStore((state) => state.selection);
  const clearSelection = useAppStore((state) => state.clearSelection);
  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-3 z-10 flex flex-col items-start gap-2 sm:left-5 sm:right-auto sm:bottom-5 sm:max-w-md">
      {selection.length > 0 && (
        <div className="pointer-events-auto flex items-center gap-3 rounded-full bg-panel py-1.5 pl-4 pr-1.5 ring-1 ring-gold/40 backdrop-blur-md">
          <span className="text-sm">{t('selection.count', { count: selection.length })}</span>
          <span className="font-display text-sm font-medium text-gold">
            {selection.map((z) => ELEMENTS[z - 1]?.symbol).join(' ')}
          </span>
          <button
            type="button"
            onClick={clearSelection}
            className="rounded-full px-3 py-1 text-xs text-muted ring-1 ring-rim hover:text-text"
          >
            {t('selection.clear')}
          </button>
        </div>
      )}
      <p className="rounded-2xl bg-panel/60 px-4 py-2 text-sm text-muted backdrop-blur-sm">{t('hint.table')}</p>
    </div>
  );
}

export function InfoPanel() {
  const scene = useAppStore((state) => state.scene);
  if (scene.kind === 'element') return <ElementPanel key={scene.symbol} symbol={scene.symbol} />;
  if (scene.kind === 'compound') return <CompoundPanel key={scene.id} id={scene.id} />;
  return <TableHint />;
}
