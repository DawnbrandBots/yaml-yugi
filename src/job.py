# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
import logging
from multiprocessing import current_process
import os
import sys
from typing import Any, Dict, List, Optional, Union

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
import wikitextparser as wtp


module_logger = logging.getLogger(__name__)


def expand_templates(template: wtp.Template) -> str:
    if template.name.strip().lower() == "ruby":
        base = template.arguments[0].value.strip()
        ruby = template.arguments[1].value.strip()
        # <rp>（</rp>
        # <rp>）</rp>
        return f"<ruby>{base}<rt>{ruby}</rt></ruby>"
    else:
        return ""


def initial_parse(yaml: YAML, yaml_file: str) -> Dict[str, str]:
    with open(yaml_file) as f:
        document = yaml.load(f)
    properties = {}
    wikitext = wtp.parse(document["wikitext"])
    assert len(wikitext.templates)
    for template in wikitext.templates:
        if template.name.strip() == "CardTable2":
            break
    for argument in template.arguments:
        name = argument.name.strip()
        value = argument.value.strip().replace("<br />", "\n").replace("<br/>", "\n")
        value = wtp.remove_markup(value, replace_templates=expand_templates)
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


def annotate_zh_cn(yaml: YAML, logger: logging.Logger, zh_cn_dir: str, wikitext: Dict[str, str]) -> None:
    password = int_or_none(wikitext.get("password") or "")
    zh_cn_path = os.path.join(zh_cn_dir, f"{password}.yaml")
    if os.path.isfile(zh_cn_path):
        logger.info(f"zh-CN: {zh_cn_path}")
        with open(zh_cn_path) as f:
            document = yaml.load(f)
            wikitext["ourocg_name"] = document["name"]
            wikitext["ourocg_text"] = document["text"]
            if document.get("pendulum"):
                wikitext["ourocg_pendulum"] = document["pendulum"]


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
            module_logger.warning(f"Sets missing second semicolon: {printing}")
        result.append({
            "set_number": set_number.strip(),
            "set_name": set_name.strip(),
            "rarities": rarities.split(", ") if rarities else None
        })
    return result


LINK_ARROW_MAPPING = {
    "Bottom-Left": "↙",
    "Bottom-Center": "⬇",  # YGOPRODECK: Bottom
    "Bottom-Right": "↘",
    "Middle-Left": "⬅",  # YGOPRODECK: Left
    "Middle-Right": "➡",  # YGOPRODECK: Right
    "Top-Left": "↖",
    "Top-Center": "⬆",  # YGOPRODECK: Top
    "Top-Right": "↗"
}


def transform_structure(logger: logging.Logger, wikitext: Dict[str, str]) -> Optional[Dict[str, Any]]:
    if (
        # Normal monster version OCG prize cards, Tyler, OG Egyptian Gods
        wikitext.get("database_id") == "none" or
        # Match winners, Command Duel-Use Card (only one with dbid None), etc. have db ids but no passwords
        "limitation_text" in wikitext or
        # Boss Duel cards
        wikitext.get("ocg_status") == "Illegal"
    ):
        logger.info(f"Skip: {wikitext}")
        return
    konami_id = int_or_none(wikitext.get("database_id"))
    password = int_or_none(wikitext.get("password"))
    document = {
        "konami_id": konami_id,
        "password": password,
        "name": {
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
            "zh-CN": wikitext.get("sc_name") or wikitext.get("ourocg_name")
        },
        "text": {
            "en": str_or_none(wikitext.get("lore")),  # should never be none
            "de": str_or_none(wikitext.get("de_lore")),
            "es": str_or_none(wikitext.get("es_lore")),
            "fr": str_or_none(wikitext.get("fr_lore")),
            "it": str_or_none(wikitext.get("it_lore")),
            "pt": str_or_none(wikitext.get("pt_lore")),
            "ja": str_or_none(wikitext.get("ja_lore")),
            "ko": str_or_none(wikitext.get("ko_lore")),
            "zh-TW": str_or_none(wikitext.get("tc_lore")),
            "zh-CN": str_or_none(wikitext.get("sc_lore") or wikitext.get("ourocg_text"))
        }
    }
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
            document["link_arrows"] = [LINK_ARROW_MAPPING[arrow] for arrow in wikitext["link_arrows"].split(", ")]
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
                "zh-CN": str_or_none(wikitext.get("sc_pendulum_effect") or wikitext.get("ourocg_pendulum"))
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
    document["sets"] = {}
    if "en_sets" in wikitext:
        document["sets"]["en"] = parse_sets(wikitext["en_sets"])
    if "de_sets" in wikitext:
        document["sets"]["de"] = parse_sets(wikitext["de_sets"])
    if "es_sets" in wikitext:
        document["sets"]["es"] = parse_sets(wikitext["sp_sets"])
    if "fr_sets" in wikitext:
        document["sets"]["fr"] = parse_sets(wikitext["fr_sets"])
    if "it_sets" in wikitext:
        document["sets"]["it"] = parse_sets(wikitext["it_sets"])
    if "pt_sets" in wikitext:
        document["sets"]["pt"] = parse_sets(wikitext["pt_sets"])
    if "jp_sets" in wikitext:
        document["sets"]["ja"] = parse_sets(wikitext["jp_sets"])
    if "kr_sets" in wikitext:
        document["sets"]["ko"] = parse_sets(wikitext["kr_sets"])
    if "tc_sets" in wikitext:
        document["sets"]["zh-TW"] = parse_sets(wikitext["tc_sets"])
    if "sc_sets" in wikitext:
        document["sets"]["zh-CN"] = parse_sets(wikitext["sc_sets"])
    document["yugipedia_page_id"] = wikitext["yugipedia_page_id"]
    return document


def write_output(yaml: YAML, logger: logging.Logger, document: Dict[str, Any]) -> None:
    if document["password"] is not None:
        # Recreate eight-digit password with left-padded 0s
        filename = str(document["password"]).rjust(8, "0") + ".yaml"
    elif document["konami_id"] is not None:
        filename = f"kdb{document['konami_id']}.yaml"
    else:
        filename = f"yugipedia{document['yugipedia_page_id']}.yaml"
    logger.info(f"Write: {filename}")
    with open(filename, mode="w", encoding="utf-8") as out:
        yaml.dump(document, out)


def job(wikitext_dir: str, filenames: List[str], zh_cn_dir: Optional[str]) -> None:
    yaml = YAML()
    yaml.width = sys.maxsize
    for i, filename in enumerate(filenames):
        filepath = os.path.join(wikitext_dir, filename)
        # This should always be int, but code defensively and allow future changes to yaml-yugipedia's structure
        basename = os.path.splitext(filename)[0]
        page_id = int_or_og(basename)
        logger = module_logger.getChild(current_process().name).getChild(basename)
        logger.info(f"{i}/{len(filenames)} {filepath}")

        properties = initial_parse(yaml, filepath)
        properties["yugipedia_page_id"] = page_id
        if zh_cn_dir:
            annotate_zh_cn(yaml, logger, zh_cn_dir, properties)
        document = transform_structure(logger, properties)
        if document:
            write_output(yaml, logger, document)
