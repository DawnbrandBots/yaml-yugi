// SPDX-FileCopyrightText: © 2022 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import fs from "fs";
import yaml from "js-yaml";
import sqlite, { Database, Statement } from "better-sqlite3";
import { parseDocument } from "htmlparser2";

if (process.argv.length < 3) {
	console.error(`Usage: ${process.argv[1]} <cards.yaml>`);
	process.exit(1);
}

// This loads the aggregate file exponentially faster than ruamel.yaml somehow
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cards: any[] = yaml.loadAll(fs.readFileSync(process.argv[2], "utf8"));
console.log(`Loaded ${cards.length} cards.`);

const createStatement = fs.readFileSync(`${__dirname}/cdb.sql`, "utf8");
const outputs: Record<string, Database> = {};
const insertDatas: Record<string, Statement> = {};
const insertTexts: Record<string, Statement> = {};
const locales = ["en", "de", "es", "fr", "it", "pt", "ja", "ko", "zh-CN", "zh-TW"];
for (const locale of locales) {
    outputs[locale] = sqlite(`${locale}.cdb`);
    outputs[locale].pragma("journal_mode = WAL");
    outputs[locale].exec(createStatement);
    insertDatas[locale] = outputs[locale].prepare("REPLACE INTO datas VALUES(?,0,0,0,0,0,0,0,0,0,0)");
    insertTexts[locale] = outputs[locale].prepare("REPLACE INTO texts VALUES(?,?,?,'','','','','','','','','','','','','','','','')");
}

for (const card of cards) {
    if (card.password) {
        for (const locale of locales) {
            insertDatas[locale].run(card.password);
            insertTexts[locale].run(card.password, card.name[locale], card.text[locale]);
        }
    }
}

for (const locale of locales) {
    outputs[locale].close();
}
