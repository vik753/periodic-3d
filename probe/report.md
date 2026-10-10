# Замер источников данных (этап 0)

## Доступность источников из GitHub Actions

| Источник | HTTP | Время, с | Байт |
| --- | --- | --- | --- |
| PubChem PUG REST | 200 | 0.79 | 125 |
| PubChem 3D SDF | 200 | 0.09 | 1220 |
| QLever (Wikidata) | 200 | 0.9 | 139 |
| Wikidata Query Service | 200 | 0.58 | 167 |
| Wikidata EntityData | 200 | 0.24 | 426183 |
| Wikipedia RU REST | 200 | 0.04 | 3819 |
| Wikipedia UK REST | 200 | 0.05 | 3459 |
| Wikipedia EN REST | 200 | 0.02 | 3141 |
| Wikimedia Commons API | 200 | 0.09 | 3862 |
| COD OPTIMADE | 501 | 5.69 | 144 |
| MP OPTIMADE | 200 | 0.43 | 2430 |
| MP API heartbeat | 200 | 0.26 | 207 |
| MP open data (S3) | 200 | 0.19 | 358571 |

## Свойства Wikidata

- P274 — chemical formula
- P662 — PubChem CID
- P9902 — Materials Project material ID

## Счётчики Wikidata (QLever)

| Метрика | Значение | Время, с | Статус |
| --- | --- | --- | --- |
| formula_total | 1427642 | 1.55 | ok |
| formula_any_wiki | 27950 | 1.96 | ok |
| formula_any_wiki_with_pubchem | 23387 | 2.23 | ok |
| formula_any_wiki_without_pubchem | 4563 | 2.52 | ok |
| minerals_any_wiki | 2076 | 1.57 | ok |
| formula_enwiki | 24486 | 1.58 | ok |
| formula_ruwiki | 10070 | 0.99 | ok |
| formula_ukwiki | 4267 | 0.73 | ok |
| formula_any_wiki_with_P9902 | 1 | 0.69 | ok |

## Покрытие элементов (соединения со статьёй RU/UK/EN)

- Записей: 27950; формула разобрана: 27528; не разобрана: 422.
- С PubChem CID: 23387.
- Медиана соединений на элемент: 87.0.
- Элементы без соединений: Db, Sg, Bh, Hs, Mt, Ds, Rg, Cn, Nh, Fl, Mc, Lv.
- Элементы с 1–9 соединениями: He, Ne, Ar, Kr, At, Rn, Fr, Bk, Fm, Md, No, Lr, Rf, Ts, Og.
- Пар элементов: 1997; пар с 5+ соединениями: 826.
- Топ пар: C-H (19873), H-O (17746), C-O (16916), H-N (12594), C-N (12554), N-O (10768), H-S (3121), C-S (2955), O-S (2942), N-S (2463), Cl-H (2414), C-Cl (2382), Cl-O (2016), C-F (1888), F-H (1833).
- Число элементов в формуле (6 = 6+): {'1': 329, '2': 4202, '3': 8178, '4': 8892, '5': 4553, '6': 1374}.
- Квантили числа статей (sitelinks): {'p10': 1, 'p50': 6, 'p90': 22, 'p99': 61, 'max': 330}.

| Элемент | Соединений |
| --- | --- |
| H | 21382 |
| He | 8 |
| Li | 222 |
| Be | 97 |
| B | 364 |
| C | 20540 |
| N | 13032 |
| O | 19948 |
| F | 2474 |
| Ne | 1 |
| Na | 780 |
| Mg | 377 |
| Al | 492 |
| Si | 784 |
| P | 1340 |
| S | 3843 |
| Cl | 2987 |
| Ar | 5 |
| K | 468 |
| Ca | 506 |
| Sc | 50 |
| Ti | 176 |
| V | 141 |
| Cr | 165 |
| Mn | 267 |
| Fe | 496 |
| Co | 169 |
| Ni | 217 |
| Cu | 411 |
| Zn | 186 |
| Ga | 104 |
| Ge | 125 |
| As | 388 |
| Se | 257 |
| Br | 868 |
| Kr | 5 |
| Rb | 68 |
| Sr | 100 |
| Y | 96 |
| Zr | 119 |
| Nb | 145 |
| Mo | 136 |
| Tc | 29 |
| Ru | 97 |
| Rh | 159 |
| Pd | 265 |
| Ag | 189 |
| Cd | 83 |
| In | 84 |
| Sn | 269 |
| Sb | 172 |
| Te | 184 |
| I | 588 |
| Xe | 34 |
| Cs | 75 |
| Ba | 146 |
| La | 82 |
| Ce | 80 |
| Pr | 175 |
| Nd | 117 |
| Pm | 11 |
| Sm | 100 |
| Eu | 64 |
| Gd | 65 |
| Tb | 51 |
| Dy | 43 |
| Ho | 52 |
| Er | 37 |
| Tm | 39 |
| Yb | 65 |
| Lu | 56 |
| Hf | 44 |
| Ta | 56 |
| W | 104 |
| Re | 117 |
| Os | 105 |
| Ir | 64 |
| Pt | 335 |
| Au | 93 |
| Hg | 222 |
| Tl | 90 |
| Pb | 305 |
| Bi | 153 |
| Po | 37 |
| At | 7 |
| Rn | 5 |
| Fr | 3 |
| Ra | 14 |
| Ac | 10 |
| Th | 60 |
| Pa | 36 |
| U | 175 |
| Np | 73 |
| Pu | 132 |
| Am | 16 |
| Cm | 12 |
| Bk | 9 |
| Cf | 17 |
| Es | 10 |
| Fm | 2 |
| Md | 1 |
| No | 1 |
| Lr | 1 |
| Rf | 1 |
| Db | 0 |
| Sg | 0 |
| Bh | 0 |
| Hs | 0 |
| Mt | 0 |
| Ds | 0 |
| Rg | 0 |
| Cn | 0 |
| Nh | 0 |
| Fl | 0 |
| Mc | 0 |
| Lv | 0 |
| Ts | 1 |
| Og | 1 |

## PubChem 3D (случайная выборка соединений с CID)

- Выборка: 150; с 3D: 108 (0.72); ошибок: 0.
- Медианный размер SDF: 6866.5 байт.
- Пакетный запрос 4 CID: {'status': 200, 'records': 4, 'seconds': 0.1}.

## OPTIMADE: mp

| Формула | Reduced | HTTP | Записей | Время, с |
| --- | --- | --- | --- | --- |
| NaCl | ClNa | 200 | 154387 | 0.33 |
| Fe2O3 | Fe2O3 | 200 | 154387 | 0.22 |
| SiO2 | O2Si | 200 | 154387 | 0.2 |
| CaCO3 | CCaO3 | 200 | 154387 | 0.22 |
| Al2O3 | Al2O3 | 200 | 154387 | 0.23 |
| TiO2 | O2Ti | 200 | 154387 | 0.21 |
| Fe3O4 | Fe3O4 | 200 | 154387 | 0.21 |
| CuSO4 | CuO4S | 200 | 154387 | 0.35 |
| KMnO4 | KMnO4 | 200 | 154387 | 0.34 |
| FeS2 | FeS2 | 200 | 154387 | 0.26 |

Поля атрибутов: _mp_chemical_system, _mp_stability, assemblies, cartesian_site_positions, chemical_formula_anonymous, chemical_formula_descriptive, chemical_formula_hill, chemical_formula_reduced, dimension_types, elements, elements_ratios, immutable_id, last_modified, lattice_vectors, nelements, nperiodic_dimensions, nsites, space_group_it_number, space_group_symbol_hall, space_group_symbol_hermann_mauguin, space_group_symbol_hermann_mauguin_extended, space_group_symmetry_operations_xyz, species, species_at_sites, structure_features

## OPTIMADE: cod

| Формула | Reduced | HTTP | Записей | Время, с |
| --- | --- | --- | --- | --- |
| NaCl | ClNa | -1 | None | 2.36 |
| Fe2O3 | Fe2O3 | 501 | None | 2.23 |
| SiO2 | O2Si | 501 | None | 4.15 |
| CaCO3 | CCaO3 | 501 | None | 3.09 |
| Al2O3 | Al2O3 | -1 | None | 0.81 |
| TiO2 | O2Ti | 501 | None | 4.36 |
| Fe3O4 | Fe3O4 | 501 | None | 3.78 |
| CuSO4 | CuO4S | 501 | None | 1.73 |
| KMnO4 | KMnO4 | -1 | None | 0.52 |
| FeS2 | FeS2 | 501 | None | 3.23 |

Поля атрибутов: 

Общее время замера: 132.1 с.
