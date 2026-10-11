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

Не используем: набор GNoME в Materials Project (CC BY-NC 4.0, только некоммерческое
использование).

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
