"""Curated end uses from USGS Mineral Commodity Summaries 2026 (task U.5).

The numbers below are typed by hand from the "Domestic Production and Use" paragraphs
that tools/probe/usgs.py downloads (ci-results/probe-uses/usgs/paragraphs.json). Every
entry carries a verbatim quote; this script refuses to write the data file when a quote
is not found in the paragraph or when a share is not written in the quote.

Usage: python3 tools/probe/usgs_curate.py <paragraphs.json> pipeline/src/p3d_pipeline/uses/usgs_end_uses.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EDITION = "Mineral Commodity Summaries 2026"


def n(uk: str, ru: str, en: str) -> dict[str, str]:
    return {"uk": uk, "ru": ru, "en": en}


def s(uk: str, ru: str, en: str, share: float | None, term: str | None = None, more: bool = False) -> dict:
    item: dict = {"names": n(uk, ru, en)}
    if share is not None:
        item["share"] = share
    if term:
        item["term"] = term
    if more:
        item["more"] = True
    return item


OTHER = ("інше", "прочее", "other")

C = [
    {
        "key": "lithium",
        "commodity": n("Літій", "Литий", "Lithium"),
        "elements": ["Li"],
        "scope": "world",
        "quote": "global end uses were estimated as follows: batteries, 88%; ceramics and glass, 4%; lubricating "
        "greases, 2%; air treatment, 1%; continuous casting mold flux powders, 1%; medical, 1%; and other uses, 3%.",
        "shares": [
            s("акумулятори", "аккумуляторы", "batteries", 88, "batteries"),
            s("кераміка і скло", "керамика и стекло", "ceramics and glass", 4, "glass"),
            s("мастила", "смазки", "lubricating greases", 2, "lubricants"),
            s("очищення повітря", "очистка воздуха", "air treatment", 1),
            s("флюси для безперервного лиття", "флюсы для непрерывной разливки", "continuous casting mould flux", 1,
              "metallurgy"),
            s("медицина", "медицина", "medical", 1, "drug"),
            s(*OTHER, 3),
        ],
    },
    {
        "key": "copper",
        "commodity": n("Мідь", "Медь", "Copper"),
        "elements": ["Cu"],
        "scope": "us",
        "quote": "copper and copper alloy products were used in building construction, 42%; electrical and electronic "
        "products, 23%; transportation equipment, 18%; consumer and general products, 10%; and industrial machinery "
        "and equipment, 7%.",
        "shares": [
            s("будівництво", "строительство", "building construction", 42, "construction"),
            s("електротехніка й електроніка", "электротехника и электроника", "electrical and electronic products", 23,
              "electrical"),
            s("транспорт", "транспорт", "transportation equipment", 18, "automotive"),
            s("побутові вироби", "бытовые изделия", "consumer and general products", 10, "toys_jewelry"),
            s("промислове обладнання", "промышленное оборудование", "industrial machinery and equipment", 7),
        ],
    },
    {
        "key": "aluminum",
        "commodity": n("Алюміній", "Алюминий", "Aluminium"),
        "elements": ["Al"],
        "scope": "us",
        "quote": "Transportation applications accounted for 36% of domestic consumption; the remainder was used in "
        "packaging, 24%; building, 13%; electrical, 9%; consumer durables and machinery, 8% each; and other, 2%.",
        "shares": [
            s("транспорт", "транспорт", "transportation", 36, "automotive"),
            s("пакування", "упаковка", "packaging", 24),
            s("будівництво", "строительство", "building", 13, "construction"),
            s("електротехніка", "электротехника", "electrical", 9, "electrical"),
            s("побутові товари тривалого користування", "товары длительного пользования", "consumer durables", 8,
              "toys_jewelry"),
            s("машинобудування", "машиностроение", "machinery", 8),
            s(*OTHER, 2),
        ],
    },
    {
        "key": "antimony",
        "commodity": n("Сурма", "Сурьма", "Antimony"),
        "elements": ["Sb"],
        "scope": "us",
        "quote": "In the United States, the leading uses of antimony were metal products, including flame retardants, "
        "49%; antimonial lead and ammunition, 40%; and nonmetal products, including ceramics and glass and rubber "
        "products, 11%.",
        "shares": [
            s("металеві вироби, зокрема антипірени", "металлические изделия, в том числе антипирены",
              "metal products, including flame retardants", 49, "fire_safety"),
            s("свинцево-сурм’яні сплави й боєприпаси", "свинцово-сурьмяные сплавы и боеприпасы",
              "antimonial lead and ammunition", 40, "military"),
            s("кераміка, скло, гума", "керамика, стекло, резина", "ceramics, glass and rubber products", 11,
              "ceramics"),
        ],
        "terms": ["batteries", "glass", "rubber"],
    },
    {
        "key": "beryllium",
        "commodity": n("Берилій", "Бериллий", "Beryllium"),
        "elements": ["Be"],
        "scope": "us",
        "quote": "approximately 29% of beryllium products were used in consumer electronics, 24% in aerospace and "
        "defense applications, 17% in industrial components, 9% in automotive electronics, 8% in energy "
        "applications, 2% in semiconductor applications, and 11% in other applications.",
        "shares": [
            s("побутова електроніка", "бытовая электроника", "consumer electronics", 29, "electrical"),
            s("авіація, космос і оборона", "авиация, космос и оборона", "aerospace and defence", 24, "aerospace"),
            s("промислові деталі", "промышленные детали", "industrial components", 17),
            s("автомобільна електроніка", "автомобильная электроника", "automotive electronics", 9, "automotive"),
            s("енергетика", "энергетика", "energy applications", 8),
            s("напівпровідники", "полупроводники", "semiconductor applications", 2, "semiconductors"),
            s(*OTHER, 11),
        ],
        "terms": ["military"],
    },
    {
        "key": "cobalt",
        "commodity": n("Кобальт", "Кобальт", "Cobalt"),
        "elements": ["Co"],
        "scope": "us",
        "quote": "An estimated 51% of cobalt consumed in the United States was used in superalloys, mainly for aircraft "
        "gas turbine engines; 25% in a variety of chemical applications; 15% in various other metallic applications; "
        "and 9% in cemented carbides for cutting and wear-resistant applications.",
        "shares": [
            s("суперсплави для авіадвигунів", "суперсплавы для авиадвигателей", "superalloys for aircraft engines", 51,
              "aerospace"),
            s("хімічні застосування", "химические применения", "chemical applications", 25),
            s("інші металеві вироби", "прочие металлические изделия", "other metallic applications", 15, "alloys"),
            s("тверді сплави для різців", "твёрдые сплавы для резцов", "cemented carbides", 9, "abrasives"),
        ],
    },
    {
        "key": "gallium",
        "commodity": n("Галій", "Галлий", "Gallium"),
        "elements": ["Ga"],
        "scope": "us",
        "quote": "ICs accounted for 73% of domestic gallium consumption, and optoelectronic devices accounted for 26%.",
        "shares": [
            s("мікросхеми", "микросхемы", "integrated circuits", 73, "semiconductors"),
            s("оптоелектроніка (світлодіоди, лазери, фотодетектори)", "оптоэлектроника (светодиоды, лазеры, "
              "фотодетекторы)", "optoelectronic devices", 26, "displays"),
        ],
        "terms": ["optics_lasers", "solar", "sensors"],
    },
    {
        "key": "helium",
        "commodity": n("Гелій", "Гелий", "Helium"),
        "elements": ["He"],
        "scope": "us",
        "quote": "Helium was used for, in decreasing quantity of use, analytical, engineering, lab, science, and "
        "specialty gases (22%); controlled atmospheres, fiber optics, and semiconductors (17%); lifting gas (17%); "
        "magnetic resonance imaging (15%); aerospace (9%); welding (8%); diving (5%); leak detection (5%); and other "
        "applications (2%).",
        "shares": [
            s("аналітичні й лабораторні гази", "аналитические и лабораторные газы", "analytical, lab and science gases",
              22, "analysis"),
            s("захисні атмосфери, оптоволокно, напівпровідники", "защитные атмосферы, оптоволокно, полупроводники",
              "controlled atmospheres, fibre optics, semiconductors", 17, "semiconductors"),
            s("підйомний газ (аеростати)", "подъёмный газ (аэростаты)", "lifting gas", 17),
            s("МРТ", "МРТ", "magnetic resonance imaging", 15, "diagnostics"),
            s("авіація й космос", "авиация и космос", "aerospace", 9, "aerospace"),
            s("зварювання", "сварка", "welding", 8, "welding"),
            s("дихальні суміші для дайвінгу", "дыхательные смеси для дайвинга", "diving", 5),
            s("пошук витоків", "поиск утечек", "leak detection", 5, "sensors"),
            s(*OTHER, 2),
        ],
        "terms": ["optics_lasers"],
    },
    {
        "key": "helium",
        "commodity": n("Неон", "Неон", "Neon"),
        "elements": ["Ne"],
        "scope": "us",
        "quote": "Neon was used for, in decreasing quantity of use, lamps (53%), semiconductors (32%), plasma displays "
        "(12%), and other (3%).",
        "shares": [
            s("лампи", "лампы", "lamps", 53, "lighting"),
            s("напівпровідники", "полупроводники", "semiconductors", 32, "semiconductors"),
            s("плазмові екрани", "плазменные экраны", "plasma displays", 12, "displays"),
            s(*OTHER, 3),
        ],
    },
    {
        "key": "helium",
        "commodity": n("Аргон", "Аргон", "Argon"),
        "elements": ["Ar"],
        "scope": "us",
        "quote": "Argon was used for welding (66%), steelmaking (20%), electronics (10%), and other (4%).",
        "shares": [
            s("зварювання", "сварка", "welding", 66, "welding"),
            s("виплавлення сталі", "выплавка стали", "steelmaking", 20, "metallurgy"),
            s("електроніка", "электроника", "electronics", 10, "electrical"),
            s(*OTHER, 4),
        ],
    },
    {
        "key": "helium",
        "commodity": n("Криптон", "Криптон", "Krypton"),
        "elements": ["Kr"],
        "scope": "us",
        "quote": "Krypton was used for semiconductors (67%), lamps (20%), insulated glass (10%), and other (3%).",
        "shares": [
            s("напівпровідники", "полупроводники", "semiconductors", 67, "semiconductors"),
            s("лампи", "лампы", "lamps", 20, "lighting"),
            s("склопакети", "стеклопакеты", "insulated glass", 10, "glass"),
            s(*OTHER, 3),
        ],
    },
    {
        "key": "helium",
        "commodity": n("Ксенон", "Ксенон", "Xenon"),
        "elements": ["Xe"],
        "scope": "us",
        "quote": "Xenon was used for lamps (37%), semiconductors (36%), lasers (13%), medical (6%), and other (8%).",
        "shares": [
            s("лампи", "лампы", "lamps", 37, "lighting"),
            s("напівпровідники", "полупроводники", "semiconductors", 36, "semiconductors"),
            s("лазери", "лазеры", "lasers", 13, "optics_lasers"),
            s("медицина", "медицина", "medical", 6, "drug"),
            s(*OTHER, 8),
        ],
    },
    {
        "key": "iodine",
        "commodity": n("Йод", "Йод", "Iodine"),
        "elements": ["I"],
        "scope": "world",
        "ranked": True,
        "quote": "Worldwide, the leading uses of iodine and its compounds were, in descending order of quantity "
        "consumed, X-ray contrast media (XRCM), liquid crystal displays (LCDs), pharmaceuticals, iodophors, animal "
        "feed, and fluorochemicals.",
        "shares": [
            s("рентгеноконтрастні речовини", "рентгеноконтрастные вещества", "X-ray contrast media", None,
              "diagnostics"),
            s("рідкокристалічні екрани", "жидкокристаллические экраны", "liquid crystal displays", None, "displays"),
            s("ліки", "лекарства", "pharmaceuticals", None, "drug"),
            s("йодофори (антисептики)", "йодофоры (антисептики)", "iodophors", None, "antiseptic"),
            s("корми для тварин", "корма для животных", "animal feed", None, "animal_feed"),
            s("фторорганічна хімія", "фторорганическая химия", "fluorochemicals", None, "chemical_feedstock"),
        ],
        "terms": ["biocide", "fortification", "plastics"],
    },
    {
        "key": "mercury",
        "commodity": n("Ртуть", "Ртуть", "Mercury"),
        "elements": ["Hg"],
        "scope": "us",
        "year": "2021",
        "quote": "The leading domestic end uses of mercury and mercury compounds were relays, sensors, switches, and "
        "valves, 65%; dental amalgam, 27%; formulated products (buffers, catalysts, fixatives, and vaccination uses), "
        "7%; and bulbs, lamps, and lighting, 1%.",
        "shares": [
            s("реле, датчики, перемикачі, клапани", "реле, датчики, переключатели, клапаны",
              "relays, sensors, switches and valves", 65, "sensors"),
            s("зубна амальгама", "зубная амальгама", "dental amalgam", 27, "dental"),
            s("готові препарати (буфери, каталізатори, вакцини)", "готовые препараты (буферы, катализаторы, вакцины)",
              "formulated products", 7),
            s("лампи й освітлення", "лампы и освещение", "bulbs, lamps and lighting", 1, "lighting"),
        ],
    },
    {
        "key": "selenium",
        "commodity": n("Селен", "Селен", "Selenium"),
        "elements": ["Se"],
        "scope": "world",
        "quote": "In 2025, estimated end uses for selenium in global consumption were metallurgy (including "
        "electrolytic manganese metal production), 40%; agriculture and animal health, 20%; glass manufacturing, 20%; "
        "electronics and photovoltaics, 10%; chemicals and pigments, 5%; and other applications, 5%.",
        "shares": [
            s("металургія", "металлургия", "metallurgy", 40, "metallurgy"),
            s("сільське господарство й ветеринарія", "сельское хозяйство и ветеринария",
              "agriculture and animal health", 20, "fertilizer"),
            s("виробництво скла", "производство стекла", "glass manufacturing", 20, "glass"),
            s("електроніка й сонячні батареї", "электроника и солнечные батареи", "electronics and photovoltaics", 10,
              "solar"),
            s("хімікати й пігменти", "химикаты и пигменты", "chemicals and pigments", 5, "pigments_dyes"),
            s(*OTHER, 5),
        ],
        "terms": ["cosmetics", "explosives", "catalyst", "alloys", "rubber", "plating", "animal_feed"],
    },
    {
        "key": "silver",
        "commodity": n("Срібло", "Серебро", "Silver"),
        "elements": ["Ag"],
        "scope": "us",
        "quote": "In 2025, the estimated domestic uses for silver were in electrical and electronics, 25%; other "
        "industrial uses and photography, 19%; net physical investment (bars), 18%; photovoltaics (PV), 15%; coins "
        "and medals, 14%; jewelry and silverware, 6%; and brazing and solder, 3%.",
        "shares": [
            s("електротехніка й електроніка", "электротехника и электроника", "electrical and electronics", 25,
              "electrical"),
            s("інша промисловість і фотографія", "прочая промышленность и фотография",
              "other industrial uses and photography", 19, "photography"),
            s("інвестиційні злитки", "инвестиционные слитки", "investment bars", 18),
            s("сонячні батареї", "солнечные батареи", "photovoltaics", 15, "solar"),
            s("монети й медалі", "монеты и медали", "coins and medals", 14, "toys_jewelry"),
            s("прикраси й столове срібло", "украшения и столовое серебро", "jewellery and silverware", 6),
            s("паяння", "пайка", "brazing and solder", 3, "welding"),
        ],
        "terms": ["batteries", "automotive", "plating", "printing", "optics_lasers", "water_treatment", "wood", "dental"],
    },
    {
        "key": "soda-ash",
        "commodity": n("Кальцинована сода", "Кальцинированная сода", "Soda ash"),
        "elements": ["Na"],
        "compounds": ["sodium carbonate"],
        "scope": "us",
        "quote": "the estimated distribution of soda ash by end use was glass, 45%; chemicals, 28%; miscellaneous uses, "
        "9%; distributors, 7%; soap and detergents, 5%; flue gas desulfurization, 4%; pulp and paper, 1%; and water "
        "treatment, 1%.",
        "shares": [
            s("скло", "стекло", "glass", 45, "glass"),
            s("хімічна промисловість", "химическая промышленность", "chemicals", 28, "chemical_feedstock"),
            s("різне", "разное", "miscellaneous uses", 9),
            s("дистриб’ютори", "дистрибьюторы", "distributors", 7),
            s("мило й мийні засоби", "мыло и моющие средства", "soap and detergents", 5, "cleaning"),
            s("очищення димових газів", "очистка дымовых газов", "flue gas desulfurization", 4),
            s("папір і целюлоза", "бумага и целлюлоза", "pulp and paper", 1, "pulp_paper"),
            s("очищення води", "очистка воды", "water treatment", 1, "water_treatment"),
        ],
    },
    {
        "key": "salt",
        "commodity": n("Кухонна сіль", "Поваренная соль", "Salt"),
        "elements": ["Na", "Cl"],
        "compounds": ["sodium chloride"],
        "scope": "us",
        "quote": "The chemical industry accounted for about 42% of total salt sales, with salt in brine accounting for "
        "approximately 90% of the salt used for chemical feedstock. Chlorine and caustic soda manufacturers were the "
        "main consumers within the chemical industry. Highway deicing accounted for about 37% of total salt consumed.",
        "shares": [
            s("хімічна промисловість (хлор, їдкий натр)", "химическая промышленность (хлор, едкий натр)",
              "chemical industry", 42, "chemical_feedstock"),
            s("посипання доріг узимку", "посыпка дорог зимой", "highway deicing", 37, "antifreeze"),
        ],
        "terms": ["food_processing", "water_treatment"],
    },
    {
        "key": "tellurium",
        "commodity": n("Телур", "Теллур", "Tellurium"),
        "elements": ["Te"],
        "scope": "world",
        "quote": "In 2025, estimated end uses for tellurium in global consumption were solar power cells, 70%; "
        "thermoelectric devices, 15%; metallurgy, 10%; and other applications, 5%.",
        "shares": [
            s("сонячні батареї", "солнечные батареи", "solar power cells", 70, "solar"),
            s("термоелектричні пристрої", "термоэлектрические устройства", "thermoelectric devices", 15, "electrical"),
            s("металургія", "металлургия", "metallurgy", 10, "metallurgy"),
            s(*OTHER, 5),
        ],
        "terms": ["explosives", "rubber", "catalyst", "sensors", "pigments_dyes", "glass", "ceramics"],
    },
    {
        "key": "rhenium",
        "commodity": n("Реній", "Рений", "Rhenium"),
        "elements": ["Re"],
        "scope": None,
        "quote": "The major uses of rhenium were in superalloys used in high-temperature turbine engine components and "
        "in petroleum-reforming catalysts, representing an estimated 80% and 15%, respectively, of end uses.",
        "shares": [
            s("суперсплави для турбін", "суперсплавы для турбин", "superalloys for turbine engines", 80, "aerospace"),
            s("каталізатори нафтопереробки", "катализаторы нефтепереработки", "petroleum-reforming catalysts", 15,
              "catalyst"),
        ],
        "terms": ["oil_gas", "alloys", "electrical", "sensors"],
    },
    {
        "key": "niobium",
        "commodity": n("Ніобій", "Ниобий", "Niobium"),
        "elements": ["Nb"],
        "scope": "us",
        "quote": "Major end-use distribution of domestic niobium consumption was estimated as follows: steels, about "
        "77%, and superalloys, about 23%.",
        "shares": [
            s("сталі", "стали", "steels", 77, "steel_iron"),
            s("суперсплави", "суперсплавы", "superalloys", 23, "alloys"),
        ],
        "terms": ["aerospace"],
    },
    {
        "key": "iron-steel",
        "commodity": n("Сталь", "Сталь", "Steel"),
        "elements": ["Fe"],
        "scope": "us",
        "quote": "Construction accounted for an estimated 31% of net shipments by market classification, followed by "
        "steel service centers and distributors, 26%; automotive, 15%; and steel for converting and processing, 11%; "
        "all other applications accounted for 17% of net shipments.",
        "shares": [
            s("будівництво", "строительство", "construction", 31, "construction"),
            s("сервісні центри й дистриб’ютори", "сервисные центры и дистрибьюторы",
              "service centres and distributors", 26),
            s("автомобілі", "автомобили", "automotive", 15, "automotive"),
            s("подальша переробка", "дальнейшая переработка", "converting and processing", 11),
            s(*OTHER, 17),
        ],
        "terms": ["steel_iron"],
    },
    {
        "key": "magnesium-metal",
        "commodity": n("Магній (метал)", "Магний (металл)", "Magnesium metal"),
        "elements": ["Mg"],
        "scope": "us",
        "quote": "In 2025, an estimated 69% of primary magnesium consumption was used in castings, principally for the "
        "automotive industry. Aluminum-base alloys that were used for packaging, transportation, and other "
        "applications accounted for an estimated 15% of consumption; desulfurization of iron and steel, 9%; and all "
        "other uses, 7%.",
        "shares": [
            s("литі деталі, переважно для автомобілів", "литые детали, в основном для автомобилей",
              "castings, mainly automotive", 69, "automotive"),
            s("алюмінієві сплави", "алюминиевые сплавы", "aluminium-base alloys", 15, "alloys"),
            s("десульфурація чавуну й сталі", "десульфурация чугуна и стали", "desulfurization of iron and steel", 9,
              "metallurgy"),
            s(*OTHER, 7),
        ],
    },
    {
        "key": "magnesium-compounds",
        "commodity": n("Сполуки магнію", "Соединения магния", "Magnesium compounds"),
        "elements": ["Mg"],
        "scope": "us",
        "quote": "The remaining magnesium compounds were consumed for refractories in the form of dead-burned "
        "magnesia, fused magnesia, and olivine.",
        "shares": [],
        "terms": ["refractories", "antifreeze"],
    },
    {
        "key": "potash",
        "commodity": n("Калійні солі", "Калийные соли", "Potash"),
        "elements": ["K"],
        "compounds": ["potassium chloride"],
        "scope": "us",
        "quote": "The fertilizer industry used about 85% of U.S. potash sales, and the remainder was used for chemical "
        "and industrial applications.",
        "shares": [
            s("добрива", "удобрения", "fertilizers", 85, "fertilizer"),
            s("хімія й промисловість (решта)", "химия и промышленность (остальное)",
              "chemical and industrial applications (the remainder)", 15, "chemical_feedstock"),
        ],
    },
    {
        "key": "nitrogen",
        "commodity": n("Аміак (азот)", "Аммиак (азот)", "Ammonia (nitrogen)"),
        "elements": ["N"],
        "compounds": ["ammonia"],
        "scope": "us",
        "quote": "Approximately 88% of domestic ammonia production was for fertilizer use, including anhydrous "
        "ammonia for direct application, urea, ammonium nitrates, ammonium phosphates, and other nitrogen compounds.",
        "shares": [s("добрива", "удобрения", "fertilizers", 88, "fertilizer")],
        "terms": ["explosives", "plastics", "chemical_feedstock"],
    },
    {
        "key": "phosphate",
        "commodity": n("Фосфорити", "Фосфориты", "Phosphate rock"),
        "elements": ["P"],
        "scope": "us",
        "quote": "More than 95% of the phosphate rock mined in the United States was used to manufacture wet-process "
        "phosphoric acid and superphosphoric acid, which were used as intermediate feedstocks in the manufacture of "
        "granular and liquid ammonium phosphate fertilizers and animal feed supplements.",
        "shares": [
            s("фосфорна кислота для добрив і кормів", "фосфорная кислота для удобрений и кормов",
              "phosphoric acid for fertilizers and feed", 95, "fertilizer", more=True),
        ],
        "terms": ["animal_feed", "chemical_feedstock"],
    },
    {
        "key": "strontium",
        "commodity": n("Стронцій", "Стронций", "Strontium"),
        "elements": ["Sr"],
        "scope": "us",
        "quote": "the estimated end-use distribution in the United States for strontium, including celestite and "
        "strontium compounds, was drilling fluids, 65%; ceramic ferrite magnets and pyrotechnics and signals, 14% "
        "each; and other uses, including electrolytic production of zinc, glass, master alloys, and pigments and "
        "fillers, 7%.",
        "shares": [
            s("бурові розчини", "буровые растворы", "drilling fluids", 65, "oil_gas"),
            s("феритові магніти", "ферритовые магниты", "ceramic ferrite magnets", 14, "magnets"),
            s("піротехніка й сигнальні ракети", "пиротехника и сигнальные ракеты", "pyrotechnics and signals", 14,
              "pyrotechnics"),
            s(*OTHER, 7),
        ],
        "terms": ["glass", "alloys", "pigments_dyes"],
    },
    {
        "key": "tin",
        "commodity": n("Олово", "Олово", "Tin"),
        "elements": ["Sn"],
        "scope": "us",
        "quote": "The uses for tin in the United States were chemicals, 25%; tinplate, 16%; alloys, 12%; solder, 11%; "
        "babbitt, brass and bronze, and tinning, 7%; bar tin, 2%; and other, 27%.",
        "shares": [
            s("хімічні сполуки", "химические соединения", "chemicals", 25, "chemical_feedstock"),
            s("білу жесть", "белая жесть", "tinplate", 16, "plating"),
            s("сплави", "сплавы", "alloys", 12, "alloys"),
            s("припої", "припои", "solder", 11, "welding"),
            s("бабіт, латунь, бронза, лудіння", "баббит, латунь, бронза, лужение", "babbitt, brass, bronze, tinning",
              7),
            s("олово в зливках", "олово в слитках", "bar tin", 2),
            s(*OTHER, 27),
        ],
    },
    {
        "key": "tungsten",
        "commodity": n("Вольфрам", "Вольфрам", "Tungsten"),
        "elements": ["W"],
        "scope": "us",
        "quote": "An estimated 60% of the tungsten consumed in the United States was used in cemented carbide parts "
        "for cutting and wear-resistant applications, primarily in the construction, metalworking, mining, and oil- "
        "and gas-drilling industries.",
        "shares": [
            s("тверді сплави для різання й буріння", "твёрдые сплавы для резания и бурения", "cemented carbide parts",
              60, "abrasives"),
        ],
        "terms": ["alloys", "steel_iron", "electrical", "lighting", "welding"],
    },
    {
        "key": "vanadium",
        "commodity": n("Ванадій", "Ванадий", "Vanadium"),
        "elements": ["V"],
        "scope": "us",
        "quote": "Metallurgical use, primarily as an alloying agent for iron and steel, accounted for more than 90% of "
        "domestic reported vanadium consumption in 2025.",
        "shares": [
            s("легування чавуну й сталі", "легирование чугуна и стали", "alloying of iron and steel", 90,
              "steel_iron", more=True),
        ],
        "terms": ["catalyst"],
    },
    {
        "key": "nickel",
        "commodity": n("Нікель", "Никель", "Nickel"),
        "elements": ["Ni"],
        "scope": "us",
        "quote": "Stainless and alloy steel and nickel-containing alloys typically account for more than 85% of "
        "domestic consumption.",
        "shares": [
            s("нержавіюча сталь і сплави", "нержавеющая сталь и сплавы", "stainless steel and alloys", 85,
              "steel_iron", more=True),
        ],
        "terms": ["alloys", "plating", "catalyst"],
    },
    {
        "key": "lead",
        "commodity": n("Свинець", "Свинец", "Lead"),
        "elements": ["Pb"],
        "scope": "us",
        "quote": "The lead-acid battery industry accounted for an estimated 67% of U.S. apparent consumption of lead "
        "during 2025.",
        "shares": [s("свинцево-кислотні акумулятори", "свинцово-кислотные аккумуляторы", "lead-acid batteries", 67,
                     "batteries")],
        "terms": ["automotive"],
    },
    {
        "key": "arsenic",
        "commodity": n("Миш’як", "Мышьяк", "Arsenic"),
        "elements": ["As"],
        "scope": "us",
        "quote": "Domestically, the leading use of arsenic was for the production of herbicides, insecticides, and "
        "wood preservatives (more than 80%), followed by metallurgical and semiconductor applications.",
        "shares": [
            s("гербіциди, інсектициди, захист деревини", "гербициды, инсектициды, защита древесины",
              "herbicides, insecticides and wood preservatives", 80, "wood", more=True),
        ],
        "terms": ["herbicide", "insecticide", "semiconductors", "alloys", "batteries"],
    },
    {
        "key": "barite",
        "commodity": n("Барит", "Барит", "Barite"),
        "elements": ["Ba"],
        "compounds": ["barium sulfate", "baryte"],
        "scope": "us",
        "quote": "Typically, more than 90% of the barite sold in the United States is used as a weighting agent in "
        "fluids used in the drilling of oil and natural gas wells.",
        "shares": [
            s("бурові розчини для нафтових і газових свердловин", "буровые растворы для нефтяных и газовых скважин",
              "drilling fluids for oil and gas wells", 90, "oil_gas", more=True),
        ],
        "terms": ["paints_coatings", "plastics", "rubber", "automotive", "construction", "diagnostics"],
    },
    {
        "key": "rare-earths",
        "commodity": n("Рідкісноземельні елементи", "Редкоземельные элементы", "Rare earths"),
        "elements": ["La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu"],
        "scope": None,
        "quote": "The estimated leading domestic end use of rare earths was catalysts, whereas the estimated leading "
        "global use was magnets. Other end uses included batteries, ceramics and glass, metallurgical applications "
        "and alloys, and polishing.",
        "shares": [],
        "terms": ["catalyst", "magnets", "batteries", "ceramics", "glass", "alloys", "abrasives"],
    },
    {
        "key": "yttrium",
        "commodity": n("Ітрій", "Иттрий", "Yttrium"),
        "elements": ["Y"],
        "scope": "world",
        "quote": "The leading domestic and global end uses of yttrium were in ceramics and phosphors. Lesser amounts "
        "were consumed for fiber optics, optical glass, pigments and other applications, including "
        "yttrium-aluminum-garnet crystals used in lasers for communication, industrial, and medical applications.",
        "shares": [],
        "terms": ["ceramics", "lighting", "optics_lasers", "glass", "pigments_dyes"],
    },
    {
        "key": "scandium",
        "commodity": n("Скандій", "Скандий", "Scandium"),
        "elements": ["Sc"],
        "scope": None,
        "quote": "The principal uses for scandium in 2025 were in aerospace alloys and solid oxide fuel cells used in "
        "large-scale power generation and backup power systems for critical infrastructure.",
        "shares": [],
        "terms": ["aerospace", "alloys", "fuel_cells"],
    },
    {
        "key": "zirconium",
        "commodity": n("Циркон", "Циркон", "Zircon"),
        "elements": ["Zr"],
        "compounds": ["zircon"],
        "scope": None,
        "quote": "The leading end use for zircon was ceramics. Other primary uses of zircon included foundry sand, "
        "refractories, and zirconium chemicals.",
        "shares": [],
        "terms": ["ceramics", "metallurgy", "refractories"],
    },
    {
        "key": "hafnium",
        "commodity": n("Гафній", "Гафний", "Hafnium"),
        "elements": ["Hf"],
        "scope": None,
        "quote": "The leading use of hafnium metal was in superalloys.",
        "shares": [],
        "terms": ["alloys"],
    },
    {
        "key": "titanium",
        "commodity": n("Титан (метал)", "Титан (металл)", "Titanium metal"),
        "elements": ["Ti"],
        "scope": "us",
        "quote": "the majority of titanium metal was used in aerospace applications, and the remainder was used in "
        "armor, chemical processing, marine hardware, medical implants, power generation, and other applications.",
        "shares": [],
        "terms": ["aerospace", "military"],
    },
    {
        "key": "indium",
        "commodity": n("Індій", "Индий", "Indium"),
        "elements": ["In"],
        "scope": "world",
        "quote": "Production of indium tin oxide (ITO) continued to account for most global indium consumption.",
        "shares": [],
        "terms": ["displays", "alloys", "welding", "semiconductors", "research"],
    },
    {
        "key": "germanium",
        "commodity": n("Германій", "Германий", "Germanium"),
        "elements": ["Ge"],
        "scope": "us",
        "quote": "A company in St. George, UT, produced germanium wafers mostly for solar cells used in satellites from "
        "imported and recycled germanium. A company in Quapaw, OK, produced germanium tetrachloride for the "
        "production of fiber optics from imported and recycled germanium materials.",
        "shares": [],
        "terms": ["solar", "aerospace", "optics_lasers"],
    },
    {
        "key": "graphite",
        "commodity": n("Графіт", "Графит", "Graphite"),
        "elements": ["C"],
        "compounds": ["graphite"],
        "scope": "us",
        "quote": "Natural graphite was widely used in batteries, brake linings, lubricants, powdered metals, refractory "
        "applications, and steelmaking, and was also incorporated into some defense-related materials and components.",
        "shares": [],
        "terms": ["batteries", "automotive", "lubricants", "refractories", "steel_iron", "military"],
    },
    {
        "key": "diamond",
        "commodity": n("Технічні алмази", "Технические алмазы", "Industrial diamond"),
        "elements": ["C"],
        "compounds": ["diamond"],
        "scope": "us",
        "quote": "The major consuming sectors of industrial diamond are computer chip production; construction; "
        "drilling for minerals, natural gas, and oil; machinery manufacturing; stone cutting and polishing; and "
        "transportation (infrastructure and vehicles).",
        "shares": [],
        "terms": ["semiconductors", "construction", "oil_gas", "abrasives"],
    },
    {
        "key": "fluorspar",
        "commodity": n("Флюорит", "Флюорит", "Fluorspar"),
        "elements": ["F"],
        "compounds": ["calcium fluoride", "fluorite"],
        "scope": "us",
        "quote": "Aqueous HF is the primary feedstock for the manufacture of virtually all fluorine-bearing chemicals, "
        "particularly refrigerants and fluoropolymers, and chemicals used in the processing of primary aluminum and "
        "uranium.",
        "shares": [],
        "terms": ["chemical_feedstock", "refrigerant", "plastics", "metallurgy"],
    },
    {
        "key": "manganese",
        "commodity": n("Марганець", "Марганец", "Manganese"),
        "elements": ["Mn"],
        "scope": "us",
        "quote": "Other companies consumed ore for nonmetallurgical purposes, such as in the production of animal "
        "feed, brick colorant, dry cell batteries, and fertilizers.",
        "shares": [],
        "terms": ["steel_iron", "alloys", "animal_feed", "pigments_dyes", "batteries", "fertilizer"],
    },
    {
        "key": "molybdenum",
        "commodity": n("Молібден", "Молибден", "Molybdenum"),
        "elements": ["Mo"],
        "scope": None,
        "quote": "Molybdenum is a refractory metallic element used principally as an alloying agent in cast iron, "
        "steel, and superalloys and is also used in numerous chemical applications, including catalysts, lubricants, "
        "and pigments.",
        "shares": [],
        "terms": ["alloys", "steel_iron", "catalyst", "lubricants", "pigments_dyes"],
    },
    {
        "key": "chromium",
        "commodity": n("Хром", "Хром", "Chromium"),
        "elements": ["Cr"],
        "scope": "us",
        "quote": "Stainless-steel and heat-resisting-steel producers were the leading consumers of ferrochromium.",
        "shares": [],
        "terms": ["steel_iron", "alloys"],
    },
    {
        "key": "zinc",
        "commodity": n("Цинк", "Цинк", "Zinc"),
        "elements": ["Zn"],
        "scope": "us",
        "ranked": True,
        "quote": "Of the total reported zinc consumed, most was used to produce galvanized steel, followed by brass and "
        "bronze, zinc-base alloys, and other uses.",
        "shares": [
            s("оцинкована сталь", "оцинкованная сталь", "galvanized steel", None, "plating"),
            s("латунь і бронза", "латунь и бронза", "brass and bronze", None, "alloys"),
            s("цинкові сплави", "цинковые сплавы", "zinc-base alloys", None),
            s(*OTHER, None),
        ],
    },
    {
        "key": "silicon",
        "commodity": n("Кремній (метал)", "Кремний (металл)", "Silicon metal"),
        "elements": ["Si"],
        "scope": "us",
        "quote": "The main consumers of silicon metal were producers of aluminum alloys and the chemical industry, in "
        "particular for the manufacture of silicones.",
        "shares": [],
        "terms": ["alloys", "plastics", "chemical_feedstock"],
    },
    {
        "key": "boron",
        "commodity": n("Бор", "Бор", "Boron"),
        "elements": ["B"],
        "scope": "us",
        "quote": "In 2025, the glass and ceramics industries remained the leading domestic users of boron products. "
        "Boron also was used as a component in abrasives, cleaning products, insecticides, insulation, and in the "
        "production of semiconductors.",
        "shares": [],
        "terms": ["glass", "ceramics", "abrasives", "cleaning", "insecticide", "construction", "semiconductors"],
    },
    {
        "key": "bromine",
        "commodity": n("Бром", "Бром", "Bromine"),
        "elements": ["Br"],
        "scope": "world",
        "quote": "The leading global applications of bromine are for the production of brominated flame retardants "
        "(BFRs) and clear brine drilling fluids.",
        "shares": [],
        "terms": ["fire_safety", "oil_gas", "chemical_feedstock", "water_treatment"],
    },
    {
        "key": "cadmium",
        "commodity": n("Кадмій", "Кадмий", "Cadmium"),
        "elements": ["Cd"],
        "scope": None,
        "quote": "Cadmium metal and compounds are mainly consumed for nickel cadmium (NiCd) batteries, but also for "
        "alloys, coatings, and pigments.",
        "shares": [],
        "terms": ["batteries", "alloys", "plating", "pigments_dyes", "solar", "sensors"],
    },
    {
        "key": "bismuth",
        "commodity": n("Вісмут", "Висмут", "Bismuth"),
        "elements": ["Bi"],
        "scope": "us",
        "quote": "Most domestic bismuth consumption was for chemicals used in cosmetic, industrial, laboratory, and "
        "pharmaceutical applications.",
        "shares": [],
        "terms": ["cosmetics", "reagent", "drug", "ceramics", "pigments_dyes", "metallurgy", "alloys", "fire_safety"],
    },
    {
        "key": "cesium",
        "commodity": n("Цезій", "Цезий", "Caesium"),
        "elements": ["Cs"],
        "scope": None,
        "quote": "Cesium formate brines are used for high-pressure, high-temperature well drilling for oil and gas "
        "exploration and production.",
        "shares": [],
        "terms": ["oil_gas", "catalyst"],
    },
    {
        "key": "rubidium",
        "commodity": n("Рубідій", "Рубидий", "Rubidium"),
        "elements": ["Rb"],
        "scope": None,
        "quote": "Applications for rubidium and its compounds include biomedical research, electronics, pyrotechnics, "
        "and specialty glass.",
        "shares": [],
        "terms": ["research", "electrical", "pyrotechnics", "glass"],
    },
    {
        "key": "thallium",
        "commodity": n("Талій", "Таллий", "Thallium"),
        "elements": ["Tl"],
        "scope": None,
        "quote": "The primary end uses included the following: radioisotope thallium-201 used for medical purposes in "
        "cardiovascular imaging; thallium used as an activator (sodium iodide crystal doped with thallium) in "
        "electronics for photoelectric cells and gamma radiation detection; thallium-barium-calcium-copper-oxide "
        "high-temperature superconductors;",
        "shares": [],
        "terms": ["nuclear_medicine", "sensors", "superconductors", "optics_lasers", "glass", "catalyst"],
    },
    {
        "key": "tantalum",
        "commodity": n("Тантал", "Тантал", "Tantalum"),
        "elements": ["Ta"],
        "scope": "us",
        "quote": "Companies in the United States produced tantalum alloys, capacitors, carbides, compounds, and "
        "tantalum metal from imported tantalum ores and concentrates and tantalum-containing materials.",
        "shares": [],
        "terms": ["electrical", "alloys", "abrasives"],
    },
]


def normalize(text: str) -> str:
    text = re.sub(r"(\w)- (\w)", r"\1-\2", text)  # PDF line breaks inside hyphenated words
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline" / "src"))
    from p3d_pipeline.uses.vocabulary import TERM_BY_ID  # noqa: PLC0415

    paragraphs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    problems = []
    entries = []
    for entry in C:
        source = paragraphs[entry["key"]]
        paragraph = normalize(source["paragraph"])
        quote = normalize(entry["quote"])
        if quote.rstrip(";") not in paragraph:
            problems.append(f"{entry['commodity']['en']}: quote not in the paragraph")
        for item in entry["shares"]:
            share = item.get("share")
            if share is not None and not item["names"]["en"].endswith("(the remainder)"):
                if not re.search(rf"\b{share:g}%", quote):
                    problems.append(f"{entry['commodity']['en']}: {share}% not in the quote")
            if item.get("term") and item["term"] not in TERM_BY_ID:
                problems.append(f"{entry['commodity']['en']}: unknown term {item['term']}")
        for term in entry.get("terms", []):
            if term not in TERM_BY_ID:
                problems.append(f"{entry['commodity']['en']}: unknown term {term}")
        entries.append(
            {
                "commodity": entry["commodity"],
                "elements": entry["elements"],
                "compounds": entry.get("compounds", []),
                "edition": EDITION,
                "year": entry.get("year", "2025"),
                "scope": entry["scope"],
                "ranked": entry.get("ranked", False),
                "url": source["url"],
                "quote": quote if not quote.endswith(";") else quote[:-1] + "…",
                "shares": entry["shares"],
                "terms": entry.get("terms", []),
            }
        )
    if problems:
        raise SystemExit("\n".join(problems))
    data = {
        "source": "USGS Mineral Commodity Summaries 2026 (U.S. Geological Survey, public domain)",
        "note": "Typed by hand from the 'Domestic Production and Use' paragraphs; checked by tools/probe/usgs_curate.py.",
        "commodities": entries,
    }
    Path(sys.argv[2]).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(entries)} commodities written")


if __name__ == "__main__":
    main()
