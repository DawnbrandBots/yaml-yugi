// SPDX-FileCopyrightText: © 2022–2024 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import fs from "fs";
import yaml from "js-yaml";
import { Client } from "@opensearch-project/opensearch";
import { parseDocument } from "htmlparser2";

if (process.argv.length < 4) {
	console.error(`Usage: ${process.argv[1]} <cards.yaml> <index>`);
	process.exit(1);
}

if (process.env.OPENSEARCH_URL === undefined) {
	console.error("Missing envvar OPENSEARCH_URL");
	process.exit(1);
}

const file = process.argv[2];
const index = process.argv[3];

// This loads the aggregate file exponentially faster than ruamel.yaml somehow
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cards: any[] = yaml.loadAll(fs.readFileSync(file, "utf8"));
console.log(`Loaded ${cards.length} cards.`);

// Constructs an array of every possible combination of ruby and base text
function parseAndExpandRuby(html: string): string[] {
	let result = [""];
	const doc = parseDocument(html);
	for (const element of doc.children) {
		if (element.type === "text") {
			result = result.map(partial => `${partial}${element.data}`);
		} else if (element.type === "tag" && element.name === "ruby") {
			if (element.children.length === 2) {
				const [rb, rt] = element.children;
				if (
					rb.type === "text" &&
					rt.type === "tag" &&
					rt.name === "rt" &&
					rt.children.length === 1 &&
					rt.children[0].type === "text"
				) {
					const base = rb.data;
					const ruby = rt.children[0].data;
					result = result
						.map(partial => `${partial}${base}`)
						.concat(result.map(partial => `${partial}${ruby}`));
				} else {
					console.warn(`${html} | Unexpected <ruby> children properties`);
				}
			} else {
				console.warn(`${html} | Unexpected number of <ruby> children: ${element.children.length}`);
			}
		} else {
			console.warn(`${html} | Unexpected element type ${element.type}`);
		}
	}
	return result;
}

for (const card of cards) {
	card.expanded_name = {
		ja: card.name.ja,
		ko: card.name.ko
	};
	if (card.name.ja && card.name.ja.includes("<ruby>")) {
		card.expanded_name.ja = parseAndExpandRuby(card.name.ja);
	}
	if (card.name.ko && card.name.ko.includes("<ruby>")) {
		card.expanded_name.ko = parseAndExpandRuby(card.name.ko);
	}
}
console.log("Ruby expansion complete");

function sleep(ms: number): Promise<void> {
	return new Promise(resolve => setTimeout(resolve, ms));
}

async function retry<T>(fn: () => T | PromiseLike<T>, times = 4, max = times): Promise<T> {
	try {
		return await fn();
	} catch (error) {
		if (times === 0) {
			throw error;
		}
		const interval = 2 ** (max - times) * 5000;
		console.warn(`Failure, retrying in ${interval} ms...`);
		await sleep(interval);
		return await retry(fn, times - 1, max);
	}
}

const opensearch = new Client({ node: process.env.OPENSEARCH_URL });

(async () => {
	// Allow ? ATK/DEF to be stored
	await opensearch.indices.putMapping({
		index,
		body: {
			properties: {
				atk: {
					type: "long",
					ignore_malformed: true
				},
				def: {
					type: "long",
					ignore_malformed: true
				}
			}
		}
	});
	for (let i = 0; i < cards.length; i += 500) {
		console.log(i);
		const partition = cards.slice(i, i + 500);
		const response = await retry(() =>
			opensearch.bulk({
				index,
				body: partition.flatMap(card => [
					{ update: { _id: card.yugipedia_page_id } },
					{ doc: card, doc_as_upsert: true }
				])
			})
		);
		if (response.body.errors) {
			for (const item of response.body.items) {
				if (item.update.status !== 200) {
					console.log(item.update);
				}
			}
		}
		if (i + 500 < cards.length) {
			console.log("Done, waiting for 10000 ms...");
			await sleep(10000);
		}
	}
})();
