# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from jsonschema import validate
from ruamel.yaml import YAML


if __name__ == "__main__":
    yaml = YAML()
    with open("assignments.yaml") as f:
        assignments = yaml.load(f)
    with open("schema.yaml") as f:
        schema = yaml.load(f)
    validate(assignments, schema)
