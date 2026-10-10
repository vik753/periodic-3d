import { Scene } from './three/Scene';
import { InfoPanel } from './ui/InfoPanel';
import { RouteSync } from './ui/RouteSync';
import { TopBar } from './ui/TopBar';

export function App() {
  return (
    <>
      <RouteSync />
      <Scene />
      <TopBar />
      <InfoPanel />
    </>
  );
}
