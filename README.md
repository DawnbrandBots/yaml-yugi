# YAML Yugi

[![Merge all data sources](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/merge.yaml/badge.svg)](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/merge.yaml)
[![Validate data](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-data.yaml/badge.svg)](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-data.yaml)
[![Validate assignments.yaml](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-assignments.yaml/badge.svg)](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-assignments.yaml)

This project aims to create a comprehensive, machine-readable, human-editable database of the _Yu-Gi-Oh! Trading Card
Game_ and _Official Card Game_. It is currently incomplete and a work-in-progress.

YAML Yugi is the primary data source for the new version of Discord bot [Bastion](https://github.com/DawnbrandBots/bastion-bot).

Most card text is &copy; Studio Dice/SHUEISHA, TV TOKYO, KONAMI. They can be found under [`/data`](/data)
and on the [`aggregate`](https://github.com/DawnbrandBots/yaml-yugi/tree/aggregate) branch.

The remaining files — the actual source code of this stage of the pipeline — are available under the
GNU Affero General Public License 3.0 or later. See [COPYING](./COPYING) for more details.

The aggregate branch is very large and the history is not very relevant. It could be moved elsewhere in the future if
this is a problem. For now, it is recommended to clone this repository with the `--single-branch` flag to work on it.
If you need to fetch other branches from the remote automatically afterward, you can edit the corresponding section of
your `.git/config` file to look like this:

```
[remote "origin"]
        url = git@github.com:DawnbrandBots/yaml-yugi.git
        fetch = +refs/heads/*:refs/remotes/origin/*
        fetch = ^refs/heads/aggregate
```

## Sample links

### Individual card
- https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/cards/00010000.json (canonical download)
- https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/cards/00010000.json (CDN with correct MIME type and CORS)
- https://esm.sh/gh/DawnbrandBots/yaml-yugi/data/cards/00010000.json (alternate CDN)

### Aggregation
- https://github.com/DawnbrandBots/yaml-yugi/raw/aggregate/cards.json (canonical download)
- https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi@aggregate/rush.json (CDN, maximum 20 MB)
- https://esm.sh/gh/DawnbrandBots/yaml-yugi@aggregate/cards.json (alternate CDN)
