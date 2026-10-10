import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

export const LANGUAGES = ['uk', 'ru', 'en'] as const;
export type Language = (typeof LANGUAGES)[number];

const STORAGE_KEY = 'p3d.lang';

function isLanguage(value: string | null | undefined): value is Language {
  return value != null && (LANGUAGES as readonly string[]).includes(value);
}

function detectLanguage(): Language {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (isLanguage(saved)) return saved;
  } catch {
    // Storage can be blocked (private mode); fall back to the browser language.
  }
  const tags = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const tag of tags) {
    const base = tag.slice(0, 2).toLowerCase();
    if (isLanguage(base)) return base;
  }
  return 'en';
}

export function saveLanguage(language: Language): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Ignore: the choice still applies to this visit.
  }
}

const resources = {
  uk: {
    translation: {
      app: { title: 'Таблиця Менделєєва 3D', short: 'Таблиця 3D' },
      nav: { table: 'Таблиця', back: 'Назад', breadcrumbs: 'Де ви зараз' },
      lang: { label: 'Мова інтерфейсу' },
      category: {
        'alkali-metal': 'Лужний метал',
        'alkaline-earth-metal': 'Лужноземельний метал',
        'transition-metal': 'Перехідний метал',
        'post-transition-metal': 'Постперехідний метал',
        metalloid: 'Металоїд',
        'reactive-nonmetal': 'Неметал',
        'noble-gas': 'Інертний газ',
        lanthanide: 'Лантаноїд',
        actinide: 'Актиноїд',
        unknown: 'Властивості не вивчені',
      },
      element: {
        atomicNumber: 'Порядковий номер',
        period: 'Період',
        group: 'Група',
        groupFBlock: 'f-блок',
        block: 'Блок',
        shells: 'Електрони за оболонками',
        configuration: 'Електронна конфігурація',
        examples: 'Приклади 3D-моделей',
      },
      compound: {
        molecule: 'Молекула',
        crystal: 'Фрагмент кристалічної ґратки',
        flat: 'Плоска схема',
        composition: 'Склад',
        atoms: 'атомів',
        notFound: 'Цю сполуку не знайдено.',
      },
      hint: {
        table: 'Натисніть на елемент, щоб зануритися в нього. Shift або Ctrl + клік — вибрати кілька.',
        rotate: 'Тягніть, щоб обертати. Колесо або два пальці — наблизити.',
      },
      selection: { count: 'Вибрано: {{count}}', clear: 'Скинути вибір' },
    },
  },
  ru: {
    translation: {
      app: { title: 'Таблица Менделеева 3D', short: 'Таблица 3D' },
      nav: { table: 'Таблица', back: 'Назад', breadcrumbs: 'Где вы сейчас' },
      lang: { label: 'Язык интерфейса' },
      category: {
        'alkali-metal': 'Щелочной металл',
        'alkaline-earth-metal': 'Щёлочноземельный металл',
        'transition-metal': 'Переходный металл',
        'post-transition-metal': 'Постпереходный металл',
        metalloid: 'Полуметалл',
        'reactive-nonmetal': 'Неметалл',
        'noble-gas': 'Благородный газ',
        lanthanide: 'Лантаноид',
        actinide: 'Актиноид',
        unknown: 'Свойства не изучены',
      },
      element: {
        atomicNumber: 'Порядковый номер',
        period: 'Период',
        group: 'Группа',
        groupFBlock: 'f-блок',
        block: 'Блок',
        shells: 'Электроны по оболочкам',
        configuration: 'Электронная конфигурация',
        examples: 'Примеры 3D-моделей',
      },
      compound: {
        molecule: 'Молекула',
        crystal: 'Фрагмент кристаллической решётки',
        flat: 'Плоская схема',
        composition: 'Состав',
        atoms: 'атомов',
        notFound: 'Это соединение не найдено.',
      },
      hint: {
        table: 'Нажмите на элемент, чтобы погрузиться в него. Shift или Ctrl + клик — выбрать несколько.',
        rotate: 'Тяните, чтобы вращать. Колесо или два пальца — приблизить.',
      },
      selection: { count: 'Выбрано: {{count}}', clear: 'Сбросить выбор' },
    },
  },
  en: {
    translation: {
      app: { title: 'Periodic Table 3D', short: 'Table 3D' },
      nav: { table: 'Table', back: 'Back', breadcrumbs: 'Where you are' },
      lang: { label: 'Interface language' },
      category: {
        'alkali-metal': 'Alkali metal',
        'alkaline-earth-metal': 'Alkaline earth metal',
        'transition-metal': 'Transition metal',
        'post-transition-metal': 'Post-transition metal',
        metalloid: 'Metalloid',
        'reactive-nonmetal': 'Nonmetal',
        'noble-gas': 'Noble gas',
        lanthanide: 'Lanthanide',
        actinide: 'Actinide',
        unknown: 'Properties unknown',
      },
      element: {
        atomicNumber: 'Atomic number',
        period: 'Period',
        group: 'Group',
        groupFBlock: 'f-block',
        block: 'Block',
        shells: 'Electrons per shell',
        configuration: 'Electron configuration',
        examples: '3D model examples',
      },
      compound: {
        molecule: 'Molecule',
        crystal: 'Crystal lattice fragment',
        flat: 'Flat diagram',
        composition: 'Composition',
        atoms: 'atoms',
        notFound: 'This compound was not found.',
      },
      hint: {
        table: 'Click an element to dive in. Shift or Ctrl + click selects several.',
        rotate: 'Drag to rotate. Scroll or pinch to zoom.',
      },
      selection: { count: 'Selected: {{count}}', clear: 'Clear selection' },
    },
  },
} as const;

void i18n.use(initReactI18next).init({
  resources,
  lng: detectLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

i18n.on('languageChanged', (language) => {
  document.documentElement.lang = language;
});
document.documentElement.lang = i18n.language;

export default i18n;
