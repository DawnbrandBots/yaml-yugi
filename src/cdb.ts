// SPDX-FileCopyrightText: © 2022 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import { Static } from "@sinclair/typebox";
import sqlite, { Database, Statement } from "better-sqlite3";
import fs from "fs";
import yaml from "js-yaml";
import { CardSchema, LinkArrow, LOCALES } from "./definitions/yaml-yugi";

if (process.argv.length < 3) {
	console.error(`Usage: ${process.argv[1]} <cards.yaml>`);
	process.exit(1);
}

// This loads the aggregate file exponentially faster than ruamel.yaml somehow
const cards = yaml.loadAll(fs.readFileSync(process.argv[2], "utf8")) as Static<typeof CardSchema>[];
console.log(`Loaded ${cards.length} cards.`);

const createStatement = fs.readFileSync(`${__dirname}/cdb.sql`, "utf8");
const outputs: Record<string, Database> = {};
const insertDatas: Record<string, Statement> = {};
const insertTexts: Record<string, Statement> = {};
for (const locale of LOCALES) {
	outputs[locale] = sqlite(`${locale}.cdb`);
	outputs[locale].pragma("journal_mode = WAL");
	outputs[locale].exec(createStatement);
	insertDatas[locale] = outputs[locale].prepare("REPLACE INTO datas VALUES(?,0,0,0,0,?,?,?,?,?,0)");
	insertTexts[locale] = outputs[locale].prepare(
		"REPLACE INTO texts VALUES(?,?,?,'','','','','','','','','','','','','','','','')"
	);
}

function linkArrowsToBitset(arrows: LinkArrow[]): number {
	const MAPPING = {
		[LinkArrow["Bottom-Left"]]: 0x001,
		[LinkArrow["Bottom"]]: 0x002,
		[LinkArrow["Bottom-Right"]]: 0x004,
		[LinkArrow["Left"]]: 0x008,
		[LinkArrow["Right"]]: 0x020,
		[LinkArrow["Top-Left"]]: 0x040,
		[LinkArrow["Top"]]: 0x080,
		[LinkArrow["Top-Right"]]: 0x100
	} as const;
	return arrows.map(arrow => MAPPING[arrow]).reduce((acc, cur) => acc & cur, 0);
}

const RACE: Record<string, number> = {
	Warrior: 0x1,
	Spellcaster: 0x2,
	Fairy: 0x4,
	Fiend: 0x8,
	Zombie: 0x10,
	Machine: 0x20,
	Aqua: 0x40,
	Pyro: 0x80,
	Rock: 0x100,
	"Winged Beast": 0x200,
	Plant: 0x400,
	Insect: 0x800,
	Thunder: 0x1000,
	Dragon: 0x2000,
	Beast: 0x4000,
	"Beast-Warrior": 0x8000,
	Dinosaur: 0x10000,
	Fish: 0x20000,
	"Sea Serpent": 0x40000,
	Reptile: 0x80000,
	Psychic: 0x100000,
	"Divine-Beast": 0x200000,
	"Creator God": 0x400000,
	Wyrm: 0x800000,
	Cyberse: 0x1000000
};

const ATTRIBUTE = {
	EARTH: 0x1,
	WATER: 0x2,
	FIRE: 0x4,
	WIND: 0x8,
	LIGHT: 0x10,
	DARK: 0x20,
	DIVINE: 0x40
} as const;

for (const card of cards) {
	if (card.password) {
		for (const locale of LOCALES) {
			if (card.card_type === "Monster") {
				const [race, ...types] = card.monster_type_line.split(" / ");
				const cdbAtk = card.atk === "?" ? -2 : card.atk;
				const cdbDef =
					"link_arrows" in card ? linkArrowsToBitset(card.link_arrows) : card.def === "?" ? -2 : card.def;
				let cdbLevel = 0;
				if ("link_arrows" in card) {
					cdbLevel = card.link_arrows.length;
				} else if ("rank" in card) {
					cdbLevel = card.rank || 1;
				} else {
					cdbLevel = card.level || 12;
				}
				const cdbRace = RACE[race] || 0;
				const cdbAttribute = ATTRIBUTE[card.attribute];
				insertDatas[locale].run(card.password, cdbAtk, cdbDef, cdbLevel, cdbRace, cdbAttribute);
				insertTexts[locale].run(card.password, card.name[locale], card.text[locale]);
			} else {
				insertDatas[locale].run(card.password, 0, 0, 0, 0, 0);
				insertTexts[locale].run(card.password, card.name[locale], card.text[locale]);
			}
		}
	}
}

for (const locale of LOCALES) {
	outputs[locale].close();
}
