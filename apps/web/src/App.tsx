import { useLocation } from 'react-router';

import { Scene } from './three/Scene';
import { ElementIndex } from './ui/ElementIndex';
import { ErrorBoundary, ErrorNotice } from './ui/ErrorBoundary';
import { InfoPanel } from './ui/InfoPanel';
import { RouteSync } from './ui/RouteSync';
import { TopBar } from './ui/TopBar';

export function App() {
  const { pathname } = useLocation();
  // The 3D scene and the panel fail separately: the top bar and the way back stay.
  return (
    <>
      <RouteSync />
      <ErrorBoundary resetKey={pathname} fallback={<ErrorNotice />}>
        <Scene />
      </ErrorBoundary>
      <TopBar />
      <ElementIndex />
      <ErrorBoundary resetKey={pathname} fallback={<ErrorNotice compact />}>
        <InfoPanel />
      </ErrorBoundary>
    </>
  );
}
