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

function normalize(input: string): string {
	return input.normalize("NFKC").replaceAll("\n", "").replaceAll(/ ?● ?/g, "●").replaceAll("��", "");
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
					const official = JSON.parse(
						await fs.promises.readFile(path.join(process.argv[3], lang, `${card.konami_id}.json`), "utf8")
					);
					const discrepancy: Discrepancy = {
						yugipedia_page_id: card.yugipedia_page_id,
						konami_id: card.konami_id,
						password: card.password,
						name_en: card.name.en
					};
					const wkName = normalize(stripRuby(card.name[lang]));
					const dbName = normalize(official.name);
					if (wkName !== dbName) {
						discrepancy.name = {
							wk: wkName,
							db: dbName
						};
					}
					const wkText = normalize(stripRuby(card.text[lang]));
					const dbText = normalize(official.effectText);
					if (wkText !== dbText) {
						discrepancy.text = {
							wk: wkText,
							db: dbText
						};
					}
					if (card.pendulum_effect) {
						const wkPendulum = card.pendulum_effect[lang]
							? normalize(stripRuby(card.pendulum_effect[lang]))
							: null;
						const dbPendulum = official.pendEffect;
						if (wkPendulum != dbPendulum) {
							discrepancy.pendulum = {
								wk: wkPendulum,
								db: wkPendulum
							};
						}
					}
					if (discrepancy.name || discrepancy.text || discrepancy.pendulum) {
						discrepancies.push(discrepancy);
					}
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
				} catch (e: any) {
					console.warn(
						`Trying to find official data for ${card.konami_id}|${card.password} [${card.name.en}]`,
						e.code === "ENOENT" ? e.message : e
					);
				}
			}
		}
	}
	process.stdout.write(JSON.stringify(discrepancies, null, 2));
	process.stdout.write("\n");
	process.exitCode = Math.min(255, discrepancies.length);
})();
