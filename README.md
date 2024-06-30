# YAML Yugi

This project aims to create a comprehensive, machine-readable, human-editable database of the _Yu-Gi-Oh! Trading Card
Game_ (TCG), _Official Card Game_ (OCG), _Master Duel_ video game, _Rush Duel_, and _Speed Duel_.

YAML Yugi is the primary data source for the new version of Discord bot [Bastion](https://github.com/DawnbrandBots/bastion-bot).

Most card text is &copy; Studio Dice/SHUEISHA, TV TOKYO, KONAMI. They can be found under [`/data`](/data) and aggregations
are published to GitHub Pages.

The remaining files — the actual source code of this stage of the pipeline — are available under the
GNU Affero General Public License 3.0 or later. See [COPYING](./COPYING) for more details.

![Rush Duel cards](https://img.shields.io/badge/dynamic/json?style=flat-square&label=Rush%20Duel%20cards&query=length&url=https%3A%2F%2Fdawnbrandbots.github.io%2Fyaml-yugi%2Frush.json)
![Speed Duel Skill cards](https://img.shields.io/badge/dynamic/json?style=flat-square&label=Speed%20Duel%20Skill%20cards&query=length&url=https%3A%2F%2Fdawnbrandbots.github.io%2Fyaml-yugi%2Fskill.json)

[![Merge all data sources](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/merge.yaml/badge.svg)](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/merge.yaml)
[![Validate data](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-data.yaml/badge.svg)](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-data.yaml)
[![Validate assignments.yaml](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-assignments.yaml/badge.svg)](https://github.com/DawnbrandBots/yaml-yugi/actions/workflows/validate-assignments.yaml)

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

[Forbidden & Limited Lists (Limit Regulations)](https://github.com/DawnbrandBots/yaml-yugi-limit-regulation)

### Individual cards, JSON and YAML variants both available

#### OCG/TCG card by password
- Canonical download: https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/cards/00010000.json
- CDN with correct MIME type and CORS: https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/cards/00010000.json
- Alternative CDN: https://cdn.statically.io/gh/DawnbrandBots/yaml-yugi/master/data/cards/00010000.json

#### OCG/TCG card without password by Konami ID
- Canonical download: https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/cards/kdb5000.json
- CDN with correct MIME type and CORS: https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/cards/kdb5000.json
- Alternative CDN: https://cdn.statically.io/gh/DawnbrandBots/yaml-yugi/master/data/cards/kdb5000.json

#### Prerelease OCG/TCG card
Same as above, but with yugipedia&lt;PAGE_ID&gt; file names.

#### Rush Duel card by Konami ID
- Canonical download: https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/rush/15150.json
- CDN with correct MIME type and CORS: https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/rush/15150.json
- Alternative CDN: https://cdn.statically.io/gh/DawnbrandBots/yaml-yugi/master/data/rush/15150.json

#### TCG Speed Duel Skill Card
- Canonical download: https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/tcg-speed-skill/yugipedia585581.json
- CDN with correct MIME type and CORS: https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/tcg-speed-skill/yugipedia585581.json
- Alternative CDN: https://cdn.statically.io/gh/DawnbrandBots/yaml-yugi/master/data/tcg-speed-skill/yugipedia585581.json

### Aggregations

#### Series and archetypes, JSON and YAML both available
- As list, Canonical download: https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/series/list.json
- As list, CDN with correct MIME type and CORS: https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/series/list.json
- As list, alternative CDN: https://cdn.statically.io/gh/DawnbrandBots/yaml-yugi/master/data/series/list.json
- As mapping from English name, Canonical download: https://github.com/DawnbrandBots/yaml-yugi/raw/master/data/series/map.json
- As mapping from English name, CDN with correct MIME type and CORS: https://cdn.jsdelivr.net/gh/DawnbrandBots/yaml-yugi/data/series/map.json
- As mapping from English name, alternative CDN: https://cdn.statically.io/gh/DawnbrandBots/yaml-yugi/master/data/series/map.json

#### All OCG/TCG cards, including prereleases
- https://dawnbrandbots.github.io/yaml-yugi/cards.json
- https://dawnbrandbots.github.io/yaml-yugi/cards.yaml

#### All Rush Duel cards
- https://dawnbrandbots.github.io/yaml-yugi/rush.json
- https://dawnbrandbots.github.io/yaml-yugi/rush.yaml

#### All Master Duel cards
- https://dawnbrandbots.github.io/yaml-yugi/master-duel-raw.json

#### All TCG Speed Duel Skill Cards
- https://dawnbrandbots.github.io/yaml-yugi/skill.json
