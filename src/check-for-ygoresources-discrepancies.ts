// SPDX-FileCopyrightText: © 2024 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import fs from "fs";
import path from "path";
import { parseDocument } from "htmlparser2";

if (process.argv.length < 5) {
    console.error(`Usage: ${process.argv[1]} <data/cards> <db-ygoresources-com/yugioh-card-history> <lang>`);
    process.exit(1);
}

function stripRuby(html: string): string {
    if (!html.includes("<ruby>")) {
        return html;
    }
    let rubyless = "";
    const doc = parseDocument(html);
    for (const element of doc.children) {
        if (element.type === "text") {
            rubyless += element.data;
        } else if (element.type === "tag" && element.name === "ruby" && element.children[0].type === "text") {
            rubyless += element.children[0].data;
        }
    }
    return rubyless;
}

interface SideBySide {
    // null is only possible for no Pendulum Effect
    wk: string | null;
    db: string | null;
}

interface Discrepancy {
    yugipedia_page_id: number;
    konami_id: number;
    password: number;
    name_en: string;
    name?: SideBySide;
    text?: SideBySide;
    pendulum?: SideBySide;
}

(async () => {
    const files = await fs.promises.readdir(process.argv[2]);
    const lang = process.argv[4];
    const discrepancies = [];
    for (const file of files) {
        if (file.endsWith(".json")) {
            const card = JSON.parse(await fs.promises.readFile(path.join(process.argv[2], file), "utf8"));
            if (card.konami_id && card.sets[lang]) {
                try {
                    const official = JSON.parse(await fs.promises.readFile(path.join(process.argv[3], lang, `${card.konami_id}.json`), "utf8"));
                    const discrepancy: Discrepancy = {
                        yugipedia_page_id: card.yugipedia_page_id,
                        konami_id: card.konami_id,
                        password: card.password,
                        name_en: card.name.en
                    };
                    const name = stripRuby(card.name[lang]);
                    if (name !== official.name) {
                        discrepancy.name = {
                            wk: name,
                            db: official.name
                        };
                    }
                    const text = stripRuby(card.text[lang]).replaceAll("● ", "●");
                    if (text !== official.effectText) {
                        discrepancy.text = {
                            wk: text,
                            db: official.effectText
                        };
                    }
                    if (card.pendulum_effect) {
                        const pendulum = card.pendulum_effect[lang] ? stripRuby(card.pendulum_effect[lang]) : null;
                        if (pendulum != official.pendEffect) {
                            discrepancy.pendulum = {
                                wk: pendulum,
                                db: official.pendEffect
                            };
                        }
                    }
                    if (discrepancy.name || discrepancy.text || discrepancy.pendulum) {
                        discrepancies.push(discrepancy);
                    }
                } catch (e) {
                    console.warn(`Trying to find official data for ${card.konami_id}|${card.password} [${card.name.en}]`, e);
                }
            }
        }
    }
    process.stdout.write(JSON.stringify(discrepancies, null, 2) + "\n");
    process.exitCode = Math.min(255, discrepancies.length);
})();
