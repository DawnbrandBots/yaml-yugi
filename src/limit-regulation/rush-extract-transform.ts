// SPDX-FileCopyrightText: © 2023 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later

import * as fs from "fs";
import got from "got";
import { ElementType, parseDocument } from "htmlparser2";
import type { Element, NodeWithChildren } from "domhandler";
import { selectAll, selectOne } from "css-select";

const fetch = got.extend({ timeout: 10000, hooks: {
	beforeRequest: [
		request => {
			console.log(`Fetching ${request.url}`);
		}
	],
} });

function parseSection(className: string, table: Element): string[] {
    const siblingSelector = `td.${className} + td`;
    const container = selectOne(siblingSelector, table);
    if (!container) {
        console.warn(`${siblingSelector} not found`);
        return [];
    }
    const links = selectAll("a", container);
    return links.map(link => {
        const setNumber = link.attribs.href.split("c=")[1];
        console.log(className, ":", setNumber);
        return setNumber?.toUpperCase() ?? "";
    });
}

function parseLimitRegulation(dateHeading: Element, table: Element) {
    if (table.previousSibling?.previousSibling !== dateHeading) {
        throw new Error("Previous sibling isn't h3");
    }
    if (!dateHeading.children.length) {
        throw new Error("h3 has no children");
    }
    if (dateHeading.children[0].type !== ElementType.Text) {
        throw new Error("First child of h3 is not text");
    }
    const text = dateHeading.children[0].data;
    console.log(text);
    const match = text.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (!match) {
        throw new Error("Could not identify date");
    }
    const [, year, month, day] = match;
    const date = new Date(parseInt(year), parseInt(month) - 1 , parseInt(day));
    console.log(date);

    const forbidden = parseSection("prohibit", table);
    const limited = parseSection("limitation1", table);
    const semilimited = parseSection("limitation2", table);

    return { date, forbidden, limited, semilimited };
}

// Alternative solution: follow the link to the card preview page that has the cid
async function transformToKonamiIDs(
    { date, forbidden, limited, semilimited }: ReturnType<typeof parseLimitRegulation>,
    setNumberToCard: Map<string, any>
) {
    const forbiddenIds = forbidden.map(setNumber => setNumberToCard.get(`RD/${setNumber}`)?.konami_id);
    const limitedIds = limited.map(setNumber => setNumberToCard.get(`RD/${setNumber}`)?.konami_id);
    const semilimitedIds = semilimited.map(setNumber => setNumberToCard.get(`RD/${setNumber}`)?.konami_id);
    console.log(`Forbidden: ${forbiddenIds}`);
    console.log(`Limited: ${limitedIds}`);
    console.log(`Semi-Limited: ${semilimitedIds}`);
    const vector = Object.fromEntries([
        ...forbiddenIds.map(id => [id, 0]),
        ...limitedIds.map(id => [id, 1]),
        ...semilimitedIds.map(id => [id, 2]),
    ]);
    const file = date.toISOString().split("T")[0] + ".vector.json";
    await fs.writeFileSync(file, JSON.stringify(vector, null, 2) + "\n");
    return file;
}

(async () => {
    const rush = JSON.parse(await fs.promises.readFile(process.argv[2], { encoding: "utf-8" }));
    const setNumberToCard = new Map();
    for (const card of rush) {
        for (const set of card.sets.ja) {
            setNumberToCard.set(set.set_number, card);
        }
    }

    const main = await fetch("https://www.konami.com/yugioh/rushduel/howto/limitregulation/");
    const html = parseDocument(main.body);

    const dateHeadings = selectAll<NodeWithChildren, Element>("h3:has(+ table)", html);
    const tables = selectAll<NodeWithChildren, Element>("h3 + table", html);
    if (!dateHeadings.length) {
        throw new Error("No h3 found");
    }
    if (!tables.length) {
        throw new Error("No sibling table found");
    }
    if (dateHeadings.length !== tables.length) {
        throw new Error("Mismatch between h3 and table counts");
    }
    const files = [];
    for (let i = 0; i < tables.length; i++) {
        const parsed = parseLimitRegulation(dateHeadings[i], tables[i]);
        const file = await transformToKonamiIDs(parsed, setNumberToCard);
        files.push({ date: parsed.date, file });
    }
    // Current Forbidden & Limited List can only be one of the two most recent (most recent may yet to be effective)
    const currentFile = files[0].date < new Date() ? files[0] : files[1];
    console.log(`Currently effective: ${currentFile.date}. Most recent: ${files[0].date}`);
    await fs.promises.unlink("current.vector.json").catch(console.error);
    await fs.promises.symlink(currentFile.file, "current.vector.json");
})();
