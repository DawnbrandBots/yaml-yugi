// SPDX-FileCopyrightText: © 2022–2023 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later

import * as fs from "fs";
import got from "got";

const fetch = got.extend({ timeout: 10000, hooks: {
	beforeRequest: [
		request => {
			console.log(`Fetching ${request.url}`);
		}
	],
	afterResponse: [
		response => {
			const contentType = response.headers["content-type"];
			if (contentType !== "application/json") {
				console.warn(`Received unexpected content type [${contentType}] for ${response.requestUrl}`);
			}
			return response;
		}
	]
} });

async function transformFLList(key: string = "current"): Promise<void> {
	const request = await fetch(`https://www.yugioh-card.com/eu/_data/fllists/${key}.json`);
	const data = JSON.parse(request.body);
	const [day, month, year] = data.from.split("/");
	const rawPromise = fs.promises.writeFile(`${year}-${month}-${day}.raw.json`, request.body);

	function extractId(card: Record<string, string>): string {
		const url = new URL(card.link);
		// The null case should never happen
		return url.searchParams.get("cid") ?? card.nameeng;
	}
	
	const result: Record<string, 0 | 1 | 2> = {};
	for (const card of data["0"] ?? []) {
		result[extractId(card)] = 0;
	}
	for (const card of data["1"] ?? []) {
		result[extractId(card)] = 1;
	}
	for (const card of data["2"] ?? []) {
		result[extractId(card)] = 2;
	}
	const vectorPromise = fs.promises.writeFile(`${year}-${month}-${day}.vector.json`, `${JSON.stringify(result, null, 2)}\n`);

	return Promise.all([rawPromise, vectorPromise]).then();
}

(async () => {
	const optionsRequest = await fetch("https://www.yugioh-card.com/eu/_data/fllists/options.json");
	await fs.promises.writeFile("options.json", optionsRequest.body);
	const options = JSON.parse(optionsRequest.body);
	await Promise.all([
		transformFLList(),
		// The keys are in order and numbers as strings. Skip the largest one as it corresponds to current and might not exist.
		...Object.keys(options).reverse().slice(1).map(index => transformFLList(index))
	]);
})();
