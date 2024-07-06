# SPDX-FileCopyrightText: © 2022–2023 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from csv import DictReader
import json
import logging
from typing import Any, Dict, List, Optional, Union

import wikitextparser as wtp
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString


logger = logging.getLogger(__name__)


# Mapping of English names for languages used by Template:Unofficial name and Template:Unofficial lore
# to ISO 639-1 language codes used in our output structure
UNOFFICIAL_LANGUAGES = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
    "Portuguese": "pt",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh",
}


def set_unofficial_translation_flag(
    key: str, template: wtp.Template, output: Dict[str, Any]
) -> None:
    flags = output.setdefault("is_translation_unofficial", {}).setdefault(key, {})
    for lang in template.arguments[0].value.split(","):
        flags[UNOFFICIAL_LANGUAGES[lang.strip()]] = True


def recursive_expand_templates(wikitext: str) -> str:
    return wtp.remove_markup(wikitext, replace_templates=expand_templates).strip()


def expand_templates(template: wtp.Template) -> str:
    name = template.name.strip().lower()
    if name == "ruby":
        base = recursive_expand_templates(template.arguments[0].value)
        ruby = recursive_expand_templates(template.arguments[1].value)
        # <rp>（</rp>
        # <rp>）</rp>
        return f"<ruby>{base}<rt>{ruby}</rt></ruby>"
    elif name == "fullwidth wordwrap":
        return recursive_expand_templates(template.arguments[0].value)
    else:
        return ""


def initial_parse(
    yaml: YAML, yaml_file: str, target: str = "CardTable2"
) -> Optional[Dict[str, str]]:
    with open(yaml_file) as f:
        document = yaml.load(f)
    properties = {}
    wikitext = wtp.parse(document["wikitext"])
    if not len(wikitext.templates):
        return
    for template in wikitext.templates:
        template_name = template.name.strip()
        if template_name == target:
            break
        elif template_name == "Unofficial name":
            set_unofficial_translation_flag("name", template, properties)
        elif template_name == "Unofficial lore":
            set_unofficial_translation_flag("text", template, properties)
    if template.name.strip() != target:
        return
    for argument in template.arguments:
        name = argument.name.strip()
        value = argument.value.strip().replace("<br />", "\n").replace("<br/>", "\n")
        value = recursive_expand_templates(value)
        if value == "":
            continue
        properties[name] = value

    if "name" in properties:
        properties["en_name"] = properties.pop("name")
    else:
        # Make sure to remove page title additions like " (card)"
        properties["en_name"] = document["title"].split("(")[0].strip()
    return properties


def int_or_none(val: Optional[str]) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def int_or_og(val: str) -> Union[int, str]:
    try:
        return int(val)
    except ValueError:
        return val


def str_or_none(val: Optional[str]) -> Optional[LiteralScalarString]:
    if val:
        return LiteralScalarString(val)


# Parses a wikitext sets field value
def parse_sets(sets: str) -> List[Dict[str, str]]:
    result = []
    for printing in sets.split("\n"):
        if "; " not in printing:
            # <!-- comment for missing language release
            continue
        # There really should always be at least two semicolons in this wikitext field, even when the rarity is unknown,
        # but it gets missed, so code defensively.
        set_number, set_name, *rest = printing.split(";")
        if len(rest):
            rarities = rest[0].strip()
        else:
            rarities = None
            logger.warning(f"Sets missing second semicolon: {printing}")
        result.append(
            {
                "set_number": set_number.strip(),
                "set_name": set_name.strip(),
                "rarities": rarities.split(", ") if rarities else None,
            }
        )
    return result


# Converts all wikitext sets fields into one structured object
def transform_sets(wikitext: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
    sets = {}
    en = []
    if "en_sets" in wikitext:
        en.extend(parse_sets(wikitext["en_sets"]))
    if "na_sets" in wikitext:
        en.extend(parse_sets(wikitext["na_sets"]))
    if "eu_sets" in wikitext:
        en.extend(parse_sets(wikitext["eu_sets"]))
    if "au_sets" in wikitext:
        en.extend(parse_sets(wikitext["au_sets"]))
    if len(en):
        sets["en"] = en
    if "de_sets" in wikitext:
        sets["de"] = parse_sets(wikitext["de_sets"])
    if "es_sets" in wikitext:
        sets["es"] = parse_sets(wikitext["sp_sets"])
    if "fr_sets" in wikitext:
        sets["fr"] = parse_sets(wikitext["fr_sets"])
    if "it_sets" in wikitext:
        sets["it"] = parse_sets(wikitext["it_sets"])
    if "pt_sets" in wikitext:
        sets["pt"] = parse_sets(wikitext["pt_sets"])
    if "jp_sets" in wikitext:
        sets["ja"] = parse_sets(wikitext["jp_sets"])
    if "kr_sets" in wikitext:
        sets["ko"] = parse_sets(wikitext["kr_sets"])
    if "tc_sets" in wikitext:
        sets["zh-TW"] = parse_sets(wikitext["tc_sets"])
    if "sc_sets" in wikitext:
        sets["zh-CN"] = parse_sets(wikitext["sc_sets"])
    return sets


def transform_image_entry(entry: List[str]) -> Dict[str, str]:
    index = int_or_og(entry[0])
    image = entry[1].strip()
    result = {"index": index, "image": image}
    if len(entry) > 2:
        result["illustration"] = entry[2].strip()
    return result


def transform_image(image: str) -> List[Dict[str, str]]:
    if "\n" not in image and "; " not in image:
        return [{"index": 1, "image": image}]
    tokens = [line.split("; ") for line in image.split("\n")]
    return [transform_image_entry(entry) for entry in tokens]


def transform_names(wikitext: Dict[str, str]) -> Dict[str, str]:
    return {
        "en": wikitext["en_name"],
        "de": wikitext.get("de_name"),
        "es": wikitext.get("es_name"),
        "fr": wikitext.get("fr_name"),
        "it": wikitext.get("it_name"),
        "pt": wikitext.get("pt_name"),
        "ja": wikitext.get("ja_name"),
        "ja_romaji": wikitext.get("romaji_name"),
        "ko": wikitext.get("ko_name"),
        "ko_rr": wikitext.get("ko_rr_name"),
        "zh-TW": wikitext.get("tc_name"),
        "zh-CN": wikitext.get("sc_name"),
    }


def transform_texts(wikitext: Dict[str, str]) -> Dict[str, str]:
    return {
        "en": str_or_none(wikitext.get("lore")),  # should never be none
        "de": str_or_none(wikitext.get("de_lore")),
        "es": str_or_none(wikitext.get("es_lore")),
        "fr": str_or_none(wikitext.get("fr_lore")),
        "it": str_or_none(wikitext.get("it_lore")),
        "pt": str_or_none(wikitext.get("pt_lore")),
        "ja": str_or_none(wikitext.get("ja_lore")),
        "ko": str_or_none(wikitext.get("ko_lore")),
        "zh-TW": str_or_none(wikitext.get("tc_lore")),
        "zh-CN": str_or_none(wikitext.get("sc_lore")),
    }


def transform_multilanguage(wikitext: Dict[str, str], basename: str) -> Dict[str, str]:
    return {
        "en": str_or_none(wikitext.get(basename)),
        "de": str_or_none(wikitext.get(f"de_{basename}")),
        "es": str_or_none(wikitext.get(f"es_{basename}")),
        "fr": str_or_none(wikitext.get(f"fr_{basename}")),
        "it": str_or_none(wikitext.get(f"it_{basename}")),
        "pt": str_or_none(wikitext.get(f"pt_{basename}")),
        "ja": str_or_none(wikitext.get(f"ja_{basename}")),
        "ko": str_or_none(wikitext.get(f"ko_{basename}")),
        "zh-TW": str_or_none(wikitext.get(f"tc_{basename}")),
        "zh-CN": str_or_none(wikitext.get(f"sc_{basename}")),
    }


LINK_ARROW_MAPPING = {
    "Bottom-Left": "↙",
    "Bottom-Center": "⬇",  # YGOPRODECK: Bottom
    "Bottom-Right": "↘",
    "Middle-Left": "⬅",  # YGOPRODECK: Left
    "Middle-Right": "➡",  # YGOPRODECK: Right
    "Top-Left": "↖",
    "Top-Center": "⬆",  # YGOPRODECK: Top
    "Top-Right": "↗",
}


# Common card fields on CardTable2 between OCG and Rush Duel
def annotate_shared(document: Dict[str, Any], wikitext: Dict[str, str]) -> None:
    # Golden-Eyes Idol for some reason has card_type = Monster
    if "card_type" in wikitext and wikitext["card_type"] != "Monster":  # Spell or Trap
        document["card_type"] = wikitext["card_type"]
        document["property"] = wikitext["property"]
    else:  # Monster
        document["card_type"] = "Monster"
        document["monster_type_line"] = wikitext["types"]
        document["attribute"] = wikitext["attribute"].upper()
        if wikitext["attribute"] != document["attribute"]:
            logger.warning(f"Attribute casing: {wikitext['attribute']}")
        if "rank" in wikitext:
            document["rank"] = int(wikitext["rank"])
        elif "link_arrows" in wikitext:
            document["link_arrows"] = [
                LINK_ARROW_MAPPING[arrow]
                for arrow in wikitext["link_arrows"].split(", ")
            ]
        else:
            document["level"] = int(wikitext["level"])
        document["atk"] = int_or_og(wikitext["atk"])
        if "def" in wikitext:
            document["def"] = int_or_og(wikitext["def"])
        if "pendulum_scale" in wikitext:
            document["pendulum_scale"] = int(wikitext["pendulum_scale"])
            document["pendulum_effect"] = {
                "en": str_or_none(wikitext.get("pendulum_effect")),
                "de": str_or_none(wikitext.get("de_pendulum_effect")),
                "es": str_or_none(wikitext.get("es_pendulum_effect")),
                "fr": str_or_none(wikitext.get("fr_pendulum_effect")),
                "it": str_or_none(wikitext.get("it_pendulum_effect")),
                "pt": str_or_none(wikitext.get("pt_pendulum_effect")),
                "ja": str_or_none(wikitext.get("ja_pendulum_effect")),
                "ko": str_or_none(wikitext.get("ko_pendulum_effect")),
                "zh-TW": str_or_none(wikitext.get("tc_pendulum_effect")),
                "zh-CN": str_or_none(wikitext.get("sc_pendulum_effect")),
            }
        # bonus derived fields
        if "ritualcard" in wikitext:
            document["ritual_spell"] = wikitext["ritualcard"]
        if "materials" in wikitext:
            document["materials"] = wikitext["materials"]
    if "archseries" in wikitext:
        # Convert bulleted list to array and remove " (archetype)"
        document["series"] = [
            series.lstrip("* ").split("(")[0].rstrip()
            for series in wikitext["archseries"].split("\n")
        ]
        # In Japanese marketing, "シリーズ" (shirīzu) is always used, regardless of whether a theme has support that
        # references card names (an archetype), e.g. https://twitter.com/YuGiOh_OCG_INFO/status/690088046025445376


def write(obj: Any, basename: str, yaml: YAML, logger: logging.Logger) -> None:
    logger.info(f"Write: {basename}.yaml")
    with open(f"{basename}.yaml", mode="w", encoding="utf-8") as out:
        yaml.dump(obj, out)
    logger.info(f"Write: {basename}.json")
    with open(f"{basename}.json", mode="w", encoding="utf-8") as out:
        json.dump(obj, out)


def load_ko_csv(key: str, filename: Optional[str]) -> Dict[int, Dict[str, str]] | None:
    if not filename:
        return
    with open(filename, encoding="utf-8-sig") as f:
        reader = DictReader(f)
        return {int(row[key]): row for row in reader}


# Replace Unicode interlinear annotations with HTML markup https://www.unicode.org/charts/nameslist/n_FFF0.html
def replace_interlinear_annotations(name: str) -> str:
    return (
        name.replace("\ufff9", "<ruby>")
        .replace("\ufffa", "<rt>")
        .replace("\ufffb", "</rt></ruby>")
    )
