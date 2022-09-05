# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from datetime import datetime
import json
import os
import sys

from ruamel.yaml import YAML
import wikitextparser as wtp


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path/to/wikitexts>")
    wikitext_dir = sys.argv[1]
    yaml = YAML()
    for filename in os.listdir(wikitext_dir):
        filepath = os.path.join(wikitext_dir, filename)
        if os.path.isfile(filepath):
            with open(filepath) as f:
                document = yaml.load(f)
            wikitext = wtp.parse(document["wikitext"])
            if len(wikitext.templates) == 0:
                print(f"Skip: {filepath}")
                continue
            is_limit_regulation = False
            for template in wikitext.templates:
                if template.name.strip() == "Infobox Limited list":
                    is_limit_regulation = True
                    break
            if not is_limit_regulation:
                print(f"Skip: {filepath}")
                continue
            effective_date = None
            for argument in template.arguments:
                if argument.name.strip() == "effective_date":
                    effective_date = datetime.strptime(argument.value.strip(), "%B %d, %Y")
            if effective_date is None:
                print(f"No date for: {filepath}")
                continue
            limit_regulation = {}
            for section in wikitext.sections:
                if section.title is not None:
                    if "Forbidden" in section.title:
                        for template in section.templates:
                            if template.name == "status list name":
                                limit_regulation[template.arguments[0].value] = 0
                    if "Limited" in section.title:
                        for template in section.templates:
                            if template.name == "status list name":
                                limit_regulation[template.arguments[0].value] = 1
                    if "Semi-Limited" in section.title:
                        for template in section.templates:
                            if template.name == "status list name":
                                limit_regulation[template.arguments[0].value] = 2
            with open(effective_date.strftime("%Y-%m-%d.name.json"), "w") as f:
                json.dump(limit_regulation, f, indent=2)
