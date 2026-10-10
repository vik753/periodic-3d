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
        mass: 'Атомна маса',
        electronegativity: 'Електронегативність',
        state: 'Стан за звичайних умов',
        meltingPoint: 'Температура плавлення',
        boilingPoint: 'Температура кипіння',
        density: 'Густина',
        discovered: 'Відкриття',
        substance: 'Проста речовина',
        partners: 'Утворює сполуки з',
        compounds: 'Відомі сполуки',
        compoundCount_one: '{{count}} сполука в наборі',
        compoundCount_few: '{{count}} сполуки в наборі',
        compoundCount_many: '{{count}} сполук у наборі',
        compoundCount_other: '{{count}} сполуки в наборі',
        noCompounds: 'У наборі немає сполук цього елемента.',
        stateSolid: 'Тверда речовина',
        stateLiquid: 'Рідина',
        stateGas: 'Газ',
        unitKelvin: 'K',
        unitDensity: 'г/см³',
        stateExpected: '{{state}} (прогноз)',
        ancient: 'з давніх часів',
      },
      compound: {
        molecule: 'Молекула',
        crystal: 'Фрагмент кристалічної ґратки',
        flat: 'Плоска схема',
        composition: 'Склад',
        atoms: 'атомів',
        notFound: 'Цю сполуку не знайдено.',
        mass: 'Молярна маса',
        unitMass: 'г/моль',
        charge: 'Заряд',
        iupac: 'Назва IUPAC',
        classes: 'Тип',
        sources: 'Джерела і ліцензії',
        roleIdentity: 'Ідентифікатори',
        roleDescription: 'Опис',
        roleProperties: 'Властивості',
        roleStructure: '3D-структура',
        englishDescription: 'Опис англійською: українського ще немає.',
        noStructure: 'Для цієї сполуки поки немає 3D-моделі.',
        open: 'Відкрити картку сполуки',
      },
      hint: {
        table: 'Натисніть на елемент, щоб зануритися в нього. Shift або Ctrl + клік — вибрати кілька.',
        rotate: 'Тягніть, щоб обертати. Колесо або два пальці — наблизити.',
      },
      selection: { count: 'Вибрано: {{count}}', clear: 'Скинути вибір' },
      status: {
        loading: 'Завантаження…',
        demo: 'Демо-дані: набір даних ще не опубліковано.',
        error: 'Не вдалося завантажити дані. Перевірте з’єднання.',
      },
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
        mass: 'Атомная масса',
        electronegativity: 'Электроотрицательность',
        state: 'Состояние при обычных условиях',
        meltingPoint: 'Температура плавления',
        boilingPoint: 'Температура кипения',
        density: 'Плотность',
        discovered: 'Открытие',
        substance: 'Простое вещество',
        partners: 'Образует соединения с',
        compounds: 'Известные соединения',
        compoundCount_one: '{{count}} соединение в наборе',
        compoundCount_few: '{{count}} соединения в наборе',
        compoundCount_many: '{{count}} соединений в наборе',
        compoundCount_other: '{{count}} соединения в наборе',
        noCompounds: 'В наборе нет соединений этого элемента.',
        stateSolid: 'Твёрдое вещество',
        stateLiquid: 'Жидкость',
        stateGas: 'Газ',
        unitKelvin: 'K',
        unitDensity: 'г/см³',
        stateExpected: '{{state}} (прогноз)',
        ancient: 'с древности',
      },
      compound: {
        molecule: 'Молекула',
        crystal: 'Фрагмент кристаллической решётки',
        flat: 'Плоская схема',
        composition: 'Состав',
        atoms: 'атомов',
        notFound: 'Это соединение не найдено.',
        mass: 'Молярная масса',
        unitMass: 'г/моль',
        charge: 'Заряд',
        iupac: 'Название IUPAC',
        classes: 'Тип',
        sources: 'Источники и лицензии',
        roleIdentity: 'Идентификаторы',
        roleDescription: 'Описание',
        roleProperties: 'Свойства',
        roleStructure: '3D-структура',
        englishDescription: 'Описание на английском: русского пока нет.',
        noStructure: 'Для этого соединения пока нет 3D-модели.',
        open: 'Открыть карточку соединения',
      },
      hint: {
        table: 'Нажмите на элемент, чтобы погрузиться в него. Shift или Ctrl + клик — выбрать несколько.',
        rotate: 'Тяните, чтобы вращать. Колесо или два пальца — приблизить.',
      },
      selection: { count: 'Выбрано: {{count}}', clear: 'Сбросить выбор' },
      status: {
        loading: 'Загрузка…',
        demo: 'Демо-данные: набор данных ещё не опубликован.',
        error: 'Не удалось загрузить данные. Проверьте соединение.',
      },
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
        mass: 'Atomic mass',
        electronegativity: 'Electronegativity',
        state: 'Standard state',
        meltingPoint: 'Melting point',
        boilingPoint: 'Boiling point',
        density: 'Density',
        discovered: 'Discovered',
        substance: 'Simple substance',
        partners: 'Forms compounds with',
        compounds: 'Well-known compounds',
        compoundCount_one: '{{count}} compound in the dataset',
        compoundCount_other: '{{count}} compounds in the dataset',
        noCompounds: 'The dataset has no compounds of this element.',
        stateSolid: 'Solid',
        stateLiquid: 'Liquid',
        stateGas: 'Gas',
        unitKelvin: 'K',
        unitDensity: 'g/cm³',
        stateExpected: '{{state}} (predicted)',
        ancient: 'Ancient times',
      },
      compound: {
        molecule: 'Molecule',
        crystal: 'Crystal lattice fragment',
        flat: 'Flat diagram',
        composition: 'Composition',
        atoms: 'atoms',
        notFound: 'This compound was not found.',
        mass: 'Molar mass',
        unitMass: 'g/mol',
        charge: 'Charge',
        iupac: 'IUPAC name',
        classes: 'Type',
        sources: 'Sources and licenses',
        roleIdentity: 'Identifiers',
        roleDescription: 'Description',
        roleProperties: 'Properties',
        roleStructure: '3D structure',
        englishDescription: '',
        noStructure: 'No 3D model for this compound yet.',
        open: 'Open the compound card',
      },
      hint: {
        table: 'Click an element to dive in. Shift or Ctrl + click selects several.',
        rotate: 'Drag to rotate. Scroll or pinch to zoom.',
      },
      selection: { count: 'Selected: {{count}}', clear: 'Clear selection' },
      status: {
        loading: 'Loading…',
        demo: 'Demo data: the dataset is not published yet.',
        error: 'Could not load the data. Check the connection.',
      },
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
