import '@fontsource-variable/golos-text';
import '@fontsource-variable/unbounded';
import './styles.css';
import './i18n';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';

import { App } from './App';
import { reloadForNewVersion } from './lib/lazyChunk';

// Vite reports a chunk it could not preload (gone after a deploy): load the new page once.
window.addEventListener('vite:preloadError', (event) => {
  if (reloadForNewVersion()) event.preventDefault();
});

const queryClient = new QueryClient({
  defaultOptions: {
    // The dataset is versioned and immutable: never refetch what we already have.
    queries: { staleTime: Infinity, gcTime: 30 * 60 * 1000, refetchOnWindowFocus: false, retry: 2 },
  },
});

const basename = import.meta.env.BASE_URL.replace(/\/$/, '') || undefined;

const root = document.getElementById('root');
if (!root) throw new Error('Root element #root is missing');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={basename}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
