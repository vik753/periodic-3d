# Источники данных и лицензии

Код проекта распространяется по лицензии MIT. Химические данные сохраняют лицензии
своих источников. Каждая запись набора данных хранит источник и лицензию.

| Источник | Что берём | Лицензия | Как указываем |
| --- | --- | --- | --- |
| [PubChem](https://pubchem.ncbi.nlm.nih.gov/) (NIH) | Свойства элементов и соединений, SMILES, 3D-конформеры | Открытые данные NIH; лицензии отдельных аннотаций — у их источников | Ссылка на запись PubChem |
| [Materials Project](https://materialsproject.org/) | Кристаллические структуры (OPTIMADE) | CC BY 4.0 | Ссылка на материал MP и цитата проекта |
| [Wikidata](https://www.wikidata.org/) | Список соединений, связка идентификаторов, названия RU/UK/EN, классы, SMILES (если нет в PubChem), число статей | CC0 | Ссылка на запись Wikidata |
| [Википедия](https://www.wikipedia.org/) (RU/UK/EN) | Короткие описания | CC BY-SA 4.0 | Ссылка на статью и лицензию |
| [Wikimedia Commons](https://commons.wikimedia.org/) | Фото веществ и элементов (ссылка из Wikidata, P18) | Своя у каждого фото: CC BY-SA, CC BY, CC0, общественное достояние | Автор, лицензия и ссылка на файл — под фото |
| [RDKit](https://www.rdkit.org/) (программа, BSD) | 3D-модели, рассчитанные по SMILES, если в PubChem нет 3D | Результат расчёта; исходные SMILES — PubChem или Wikidata | «Рассчитано RDKit по SMILES» |
| [Crystallography Open Database](https://www.crystallography.net/) | Не используем: OPTIMADE у COD отвечает 501 | Общественное достояние | — |

| [ChEBI](https://www.ebi.ac.uk/chebi/) (EMBL-EBI) | Роли-применения веществ (гербицид, краситель, хладагент…) по ChEBI ID из Wikidata (P683) | CC BY 4.0 | Ссылка на запись ChEBI в разделе «Где используется» |
| Аннотации PubChem: HSDB, EPA (CDR, CPDat, HAP, Safer Choice), FDA Green Book, LiverTox, LactMed, JECFA, базы ЕС, NORMAN, IFRA, CIR и др. | Применения соединений (раздел «Где используется»): только термины словаря, правила чтения — `pipeline/src/p3d_pipeline/uses/registry.py` | У каждого источника своя: тексты правительства США — общественное достояние; остальное — факты, без цитат | Короткое имя источника и ссылка на раздел PubChem; цитаты только из общественного достояния |
| Страницы элементов PubChem (Los Alamos, Jefferson Lab, IUPAC) | Применения элементов и изотопов | Факты через PubChem, без цитат | Ссылка на страницу элемента |
| Коды ATC ВОЗ (через Wikidata, P267) | Группа лекарства (сердце, нервная система…) | Коды — CC0 (Wikidata) | Ссылка на индекс ATC/DDD |
| [USGS Mineral Commodity Summaries 2026](https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries) | Доли отраслей для 59 видов сырья, вручную, с дословной цитатой (`tools/probe/usgs_curate.py`) | Общественное достояние (правительство США) | Полоса долей, цитата и ссылка на PDF |
| [GNoME](https://github.com/google-deepmind/materials_discovery) (Google DeepMind) | Слой «Предсказанные материалы»: 554 054 кристалла, их ячейки и расчётные свойства | CC BY-NC 4.0 — только некоммерческое использование | Фиолетовая пометка «предсказано расчётом», источник, лицензия и цитата в карточке материала и на странице «О проекте» |

GNoME — отдельный слой (ADR 0007). Его материалы никогда не смешиваются с известными
соединениями: у них свой адрес (`/m/<id>`), свой цвет и пометка. Для известных
соединений GNoME по-прежнему исключён из выбора кристалла (ADR 0004). Пока сайт
показывает данные GNoME, он остаётся некоммерческим: без рекламы и платного доступа.

Цитата GNoME: A. Merchant, S. Batzner, S. S. Schoenholz, M. Aykol, G. Cheon,
E. D. Cubuk. «Scaling deep learning for materials discovery». Nature 624, 80–85 (2023).
https://doi.org/10.1038/s41586-023-06735-9

Цитата Materials Project: A. Jain, S. P. Ong, G. Hautier et al. «The Materials Project:
A materials genome approach to accelerating materials innovation». APL Materials 1,
011002 (2013).

## Как строится 3D-модель соединения

1. Минералы, металлы, ионные и сетчатые вещества (кварц) — кристалл из Materials Project.
2. Молекулы — 3D-конформер PubChem.
3. Если его нет — RDKit по SMILES (PubChem, потом Wikidata). Соли и гидраты RDKit
   строит по частям и ставит ионы рядом.
4. Для известных групп изомеров (глюкоза, ксилол) берём типичного представителя.
5. Больше 150 тяжёлых атомов — плоская схема. Нет данных — «шары состава» вместо модели.
