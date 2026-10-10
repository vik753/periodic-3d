import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router';

import { demoCompound } from '../data/demo';
import { parseSceneRoute } from '../lib/route';
import { useAppStore } from '../state/store';

/** Keeps the store's scene in sync with the URL and gives 3D code a navigate function. */
export function RouteSync() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const setScene = useAppStore((state) => state.setScene);
  const setNavigate = useAppStore((state) => state.setNavigate);
  const scene = useAppStore((state) => state.scene);

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
      const current = useAppStore.getState().scene;
      if (current.kind !== 'table') navigate('/');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate]);

  useEffect(() => {
    const app = t('app.title');
    if (scene.kind === 'element') document.title = `${scene.symbol} — ${app}`;
    else if (scene.kind === 'compound') document.title = `${demoCompound(scene.id)?.formula ?? scene.id} — ${app}`;
    else document.title = app;
  }, [scene, t]);

  return null;
}
