import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';

/** The guide videos that CI recorded for this site (guide/manifest.json, if any). */
interface GuideManifest {
  version: string;
  videos: Record<string, { src: string; poster?: string; seconds?: number }>;
}

const GUIDE_BASE = `${import.meta.env.BASE_URL}guide/`;

function useGuideManifest() {
  return useQuery({
    queryKey: ['guide-manifest'],
    queryFn: async (): Promise<GuideManifest | null> => {
      const response = await fetch(`${GUIDE_BASE}manifest.json`);
      if (!response.ok) return null;
      try {
        return (await response.json()) as GuideManifest;
      } catch {
        return null; // a dev server answers with index.html
      }
    },
    staleTime: Infinity,
    retry: false,
  });
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14" aria-hidden="true">
      <path d="M6 3.8v12.4a.8.8 0 0 0 1.2.7l10-6.2a.8.8 0 0 0 0-1.4l-10-6.2A.8.8 0 0 0 6 3.8Z" fill="currentColor" />
    </svg>
  );
}

/**
 * "Watch the video" in the How-to-use panel. The video opens over the whole screen with
 * the browser's own controls: play, pause, seek, volume, full screen. Esc, the close
 * button or a click outside the video closes it. The button shows only when the site
 * has a recorded guide.
 */
export function GuideVideoButton() {
  const { t, i18n } = useTranslation();
  const manifest = useGuideManifest();
  // /about?video opens the video at once: the README links here.
  const [params, setParams] = useSearchParams();
  const [open, setOpen] = useState(() => params.has('video'));
  const buttonRef = useRef<HTMLButtonElement>(null);
  const close = useCallback(() => {
    setOpen(false);
    setParams(
      (current) => {
        current.delete('video');
        return current;
      },
      { replace: true },
    );
    buttonRef.current?.focus();
  }, [setParams]);

  const videos = manifest.data?.videos;
  if (!videos) return null;
  const video = videos[i18n.language] ?? videos.en ?? Object.values(videos)[0];
  if (!video) return null;
  const minutes = video.seconds ? Math.max(1, Math.round(video.seconds / 60)) : null;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen(true)}
        className="group mt-4 flex w-full items-center gap-3 rounded-2xl bg-gold/10 p-3 text-left ring-1 ring-gold/40 transition-colors hover:bg-gold/20"
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-gold text-ink transition-transform group-hover:scale-105">
          <PlayIcon />
        </span>
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-text">{t('guide.watch')}</span>
          <span className="block text-xs text-muted">
            {minutes ? t('guide.length', { count: minutes }) : t('guide.hint')}
          </span>
        </span>
      </button>
      {open &&
        createPortal(
          <GuideOverlay src={`${GUIDE_BASE}${video.src}`} poster={video.poster && `${GUIDE_BASE}${video.poster}`} onClose={close} />,
          document.body,
        )}
    </>
  );
}

function GuideOverlay({ src, poster, onClose }: { src: string; poster?: string; onClose: () => void }) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.focus();
    // Start with the music. Without a click (a link that opens the video) browsers may
    // refuse sound: then start muted; the volume button in the controls turns it on.
    video.play().catch(() => {
      video.muted = true;
      void video.play().catch(() => undefined);
    });
  }, []);

  useEffect(() => {
    // Capture phase: Esc closes the video and goes no further (the page would go home).
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.stopImmediatePropagation();
      event.preventDefault();
      onClose();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('guide.title')}
      className="rise-in fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-3 backdrop-blur-md sm:p-8"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-[1120px]">
        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="font-display text-base font-semibold text-text sm:text-lg">{t('guide.title')}</p>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-2 rounded-full bg-panel px-4 py-2 text-sm text-text ring-1 ring-rim transition-colors hover:ring-gold/60"
          >
            <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
              <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            {t('guide.close')}
          </button>
        </div>
        <video
          ref={videoRef}
          src={src}
          poster={poster}
          controls
          playsInline
          preload="metadata"
          className="aspect-video w-full rounded-2xl bg-black shadow-2xl ring-1 ring-rim"
        >
          <a href={src}>{t('guide.download')}</a>
        </video>
      </div>
    </div>
  );
}
