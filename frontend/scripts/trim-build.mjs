import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../docs/app/", import.meta.url));

async function trimDirectory(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      await trimDirectory(path);
      continue;
    }
    if (!/\.(css|html|js)$/.test(entry.name)) continue;
    const source = await readFile(path, "utf8");
    const trimmed = source.replace(/[^\S\r\n]+(?=\r?\n)/g, "");
    if (trimmed !== source) await writeFile(path, trimmed, "utf8");
  }
}

await trimDirectory(root);
