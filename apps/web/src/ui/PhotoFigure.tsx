import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import type { Photo } from '../data/api';

/** A Commons photo with the attribution its license requires: author, license, source. */
export function PhotoFigure({ photo, alt }: { photo: Photo; alt: string }) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <figure className="mt-4">
      <a
        href={photo.page}
        target="_blank"
        rel="noreferrer"
        className="block overflow-hidden rounded-2xl ring-1 ring-rim"
        aria-label={t('photo.open')}
      >
        <img
          src={photo.url}
          alt={alt}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
          className="block h-44 w-full bg-white/5 object-cover"
        />
      </a>
      <figcaption className="mt-1.5 text-[11px] leading-snug text-muted">
        {t('photo.label')}: {photo.author || t('photo.unknownAuthor')},{' '}
        {photo.licenseUrl ? (
          <a
            href={photo.licenseUrl}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-rim underline-offset-2 hover:text-text"
          >
            {photo.license}
          </a>
        ) : (
          photo.license
        )}
        , Wikimedia Commons
      </figcaption>
    </figure>
  );
}
