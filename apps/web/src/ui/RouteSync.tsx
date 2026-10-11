import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router';

import { pickName } from '../data/api';
import { demoCompound } from '../data/demo';
import { useCompound, useElements, useMaterial } from '../data/hooks';
import { parseSceneRoute } from '../lib/route';
import { useAppStore } from '../state/store';

/** Keeps the store's scene in sync with the URL and gives 3D code a navigate function. */
export function RouteSync() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const setScene = useAppStore((state) => state.setScene);
  const setNavigate = useAppStore((state) => state.setNavigate);
  const scene = useAppStore((state) => state.scene);
  const elements = useElements();
  const compound = useCompound(scene.kind === 'compound' ? scene.id : null);
  const material = useMaterial(scene.kind === 'material' ? scene.id : null);

  useEffect(() => {
    setNavigate((path) => navigate(path));
  }, [navigate, setNavigate]);

  useEffect(() => {
    setScene(parseSceneRoute(location.pathname));
  }, [location.pathname, setScene]);

  // Escape goes one level up: compound → table, element → table.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const target = event.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
      const current = useAppStore.getState().scene;
      if (current.kind !== 'table') navigate('/');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate]);

  useEffect(() => {
    const app = t('app.title');
    const language = i18n.language;
    if (scene.kind === 'element') {
      const element = elements.data?.elements.find((item) => item.symbol === scene.symbol);
      const name = element ? pickName(element.names, language) : '';
      document.title = [scene.symbol, name, app].filter(Boolean).join(' — ');
    } else if (scene.kind === 'compound') {
      const demo = demoCompound(scene.id);
      const formula = demo?.formula ?? compound.data?.formula ?? scene.id;
      const name = demo ? pickName(demo.names, language) : compound.data ? pickName(compound.data.names, language) : '';
      document.title = [formula, name, app].filter(Boolean).join(' — ');
    } else if (scene.kind === 'material') {
      document.title = [material.data?.formula ?? scene.id, t('material.kind'), app].join(' — ');
    } else if (scene.kind === 'set') {
      document.title = [scene.symbols.join(' + '), app].join(' — ');
    } else {
      document.title = app;
    }
  }, [scene, t, i18n.language, elements.data, compound.data, material.data]);

  return null;
}
