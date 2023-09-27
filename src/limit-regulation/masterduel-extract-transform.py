# SPDX-FileCopyrightText: © 2023 Kevin Lu
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
            title = document["title"]
            wikitext = wtp.parse(document["wikitext"])
            if len(wikitext.templates) == 0:
                print(f"{filepath}: [{title}] skip no templates")
                continue
            if wikitext.templates[0].name.strip() != "Infobox Limited list":
                print(f"{filepath}: [{title}] skip not list")
                continue

            effective_date = None
            limit_regulation = {}
            for template in wikitext.templates:
                if template.name.strip() == "Master Duel Limitation status list":
                    for argument in template.arguments:
                        if argument.name.strip() == "date":
                            effective_date = datetime.strptime(argument.value.strip(), "%B %d, %Y")
                        if argument.name.strip() == "cards":
                            for line in argument.value.strip().split("\n"):
                                name, regulation = line.split("; ")
                                regulation = regulation.strip()
                                if regulation == "Forbidden":
                                    limit_regulation[name] = 0
                                elif regulation == "Limited":
                                    limit_regulation[name] = 1
                                elif regulation == "Semi-Limited":
                                    limit_regulation[name] = 2
                                elif regulation == "Unlimited":
                                    pass
                                else:
                                    print(f"{filepath}: [{title}] [{line}]")
                    break
            if effective_date is None:
                print(f"{filepath}: [{title}] skip no date")
                continue
            with open(effective_date.strftime("%Y-%m-%d.name.json"), "w") as f:
                json.dump(limit_regulation, f, indent=2)
