import { useTranslation } from 'react-i18next';

const ISSUES_URL = 'https://github.com/vik753/periodic-3d/issues/new';

/**
 * "Report an error": opens a new GitHub issue with the record's id, its page and a short
 * template. Visitors need a GitHub account; the issue is public, like the data.
 */
export function ReportLink({ kind, id, title }: { kind: 'compound' | 'material' | 'element'; id: string; title: string }) {
  const { t } = useTranslation();
  const page = typeof window === 'undefined' ? '' : window.location.href;
  const params = new URLSearchParams({
    title: `[${kind} ${id}] ${title}: ${t('report.titleSuffix')}`,
    body: [`${t('report.page')}: ${page}`, `ID: ${id}`, '', `${t('report.what')}:`, '', `${t('report.source')}:`, ''].join(
      '\n',
    ),
    labels: 'data',
  });
  return (
    <p className="mt-6 text-xs text-muted">
      <a
        href={`${ISSUES_URL}?${params.toString()}`}
        target="_blank"
        rel="noreferrer"
        className="underline decoration-rim underline-offset-2 hover:text-text"
      >
        {t('report.link')}
      </a>
      <span> — {t('report.hint')}</span>
    </p>
  );
}
