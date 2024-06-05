const fs = require("fs");

const aggregation = [];

for (const filename of fs.readdirSync(".")) {
	if (filename.endsWith(".json")) {
		const file = fs.readFileSync(filename, { encoding: "utf-8" });
		const card = JSON.parse(file);
		aggregation.push(card);
	}
}

fs.writeFileSync(process.argv[2], JSON.stringify(aggregation));
