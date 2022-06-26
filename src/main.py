import os
import re
import sys
from typing import Dict, List, Optional, Union, Match

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
import wikitextparser as wtp


def expand_ruby_templates(wikitext: str) -> str:
    def expand(match: Match) -> str:
        return match.expand(r"<ruby><rb>\1</rb><rp>（</rp><rt>\2</rt><rp>）</rp></ruby>")

    return re.sub(r"\{\{Ruby\|(.+?)\|(.+?)(?:\|.+?)?}}", expand, wikitext)


def transform(yaml: YAML, yaml_file: str) -> Dict[str, str]:
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
        if name != "ja_name" and name != "ko_name":
            value = wtp.remove_markup(value)
        else:
            value = expand_ruby_templates(value)
        if value == "":
            continue
        properties[name] = value

    if "name" in properties:
        properties["en_name"] = properties.pop("name")
    else:
        properties["en_name"] = document["title"]
    return properties


def int_or_none(val: str) -> Optional[int]:
    try:
        return int(val)
    except ValueError:
        return None


def int_or_og(val: str) -> Union[int, str]:
    try:
        return int(val)
    except ValueError:
        return val


def parse_sets(sets: str) -> List[Dict[str, str]]:
    result = []
    for printing in sets.split("\n"):
        if "; " not in printing:
            # <!-- comment for missing language release
            continue
        set_number, set_name, rarities, *rest = printing.split(";")
        result.append({
            "set_number": set_number.strip(),
            "set_name": set_name.strip(),
            "rarities": rarities.strip().split(", ") if rarities else None
        })
    return result


def write_output(yaml: YAML, wikitext: Dict[str, str]) -> None:
    if (
        # Pegasus/Monster B
        "database_id" not in wikitext or
        # BLS (Normal), OG Egyptian Gods
        wikitext["database_id"] == "none" or
        # Match winners, Command Duel-Use Card (only one with dbid None), etc. have db ids but no passwords
        "limitation_text" in wikitext or
        # Not yet released
        wikitext["database_id"] == ""
    ):
        print("Skip:", wikitext)
        return
    konami_id = int_or_none(wikitext["database_id"])
    password = int_or_none(wikitext.get("password") or "")
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
            "ko_rr": wikitext.get("ko_rr_name")
        },
        "text": {
            "en": LiteralScalarString(wikitext["lore"]),
            "de": LiteralScalarString(wikitext.get("de_lore")),
            "es": LiteralScalarString(wikitext.get("es_lore")),
            "fr": LiteralScalarString(wikitext.get("fr_lore")),
            "it": LiteralScalarString(wikitext.get("it_lore")),
            "pt": LiteralScalarString(wikitext.get("pt_lore")),
            "ja": LiteralScalarString(wikitext.get("ja_lore")),
            "ko": LiteralScalarString(wikitext.get("ko_lore")),
        }
    }
    # Golden-Eyes Idol for some reason has card_type = Monster
    if "card_type" in wikitext and wikitext["card_type"] != "Monster":  # Spell or Trap
        document["type"] = wikitext["card_type"]
        document["property"] = wikitext["property"]
    else:  # Monster
        document["type"] = "Monster"
        document["typeline"] = wikitext["types"]
        document["attribute"] = wikitext["attribute"]
        if "rank" in wikitext:
            document["rank"] = int(wikitext["rank"])
        elif "link_arrows" in wikitext:
            document["link_arrows"] = wikitext["link_arrows"].split(", ")
        else:
            document["level"] = int(wikitext["level"])
        document["atk"] = int_or_og(wikitext["atk"])
        if "def" in wikitext:
            document["def"] = int_or_og(wikitext["def"])
        if "pendulum_scale" in wikitext:
            document["pendulum_scale"] = int(wikitext["pendulum_scale"])
            document["pendulum_effect"] = {
                "en": LiteralScalarString(wikitext.get("pendulum_effect")),
                "de": LiteralScalarString(wikitext.get("de_pendulum_effect")),
                "es": LiteralScalarString(wikitext.get("es_pendulum_effect")),
                "fr": LiteralScalarString(wikitext.get("fr_pendulum_effect")),
                "it": LiteralScalarString(wikitext.get("it_pendulum_effect")),
                "pt": LiteralScalarString(wikitext.get("pt_pendulum_effect")),
                "ja": LiteralScalarString(wikitext.get("ja_pendulum_effect")),
                "ko": LiteralScalarString(wikitext.get("ko_pendulum_effect")),
            }
        if "materials" in wikitext:
            document["materials"] = wikitext["materials"]  # bonus derived field
        document["sets"] = {}
        if "en_sets" in wikitext:
            document["sets"]["en"] = parse_sets(wikitext["en_sets"])
        if "de_sets" in wikitext:
            document["sets"]["de"] = parse_sets(wikitext["de_sets"])
        if "es_sets" in wikitext:
            document["sets"]["es"] = parse_sets(wikitext["es_sets"])
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
    # not all have passwords, change
    if password is not None:
        filename = wikitext["password"] + ".yaml"
    else:  # konami_id is not None:
        filename = f"kdb{konami_id}.yaml"
    with open(filename, mode="w", encoding="utf-8") as out:
        yaml.dump(document, out)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path/to/wikitexts>")
    wikitext_dir = sys.argv[1]
    yaml = YAML()
    skip = True
    for filename in os.listdir(wikitext_dir):
        # if skip:
        #     if filename == "256277.yaml":
        #         skip = False
        #     else:
        #         continue
        filepath = os.path.join(wikitext_dir, filename)
        if os.path.isfile(filepath):
            print(filepath)
            properties = transform(yaml, filepath)
            write_output(yaml, properties)


if __name__ == "__main__":
    main()
