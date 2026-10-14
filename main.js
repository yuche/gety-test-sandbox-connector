import { Connector, upsert } from "@gety-ai/connector-sdk";

// Replaced per release by the publish script.
const VERSION = "__VERSION__";
const DOC_PREFIX = "__DOC_PREFIX__";

export default class SandboxTestConnector extends Connector {
  async *poll() {
    const run = (this.lastState?.run ?? 0) + 1;
    const updates = [];

    // Data-folder doc: its link points into the connector's own folder,
    // which Gety must refuse to open.
    const cachePath = `${this.dataDir}/cache.txt`;
    await Deno.writeTextFile(cachePath, `run ${run} by ${VERSION}\n`);
    updates.push(upsert({
      id: `${DOC_PREFIX}marker`,
      title: `Sandbox test marker ${VERSION}`,
      content: `Sandbox test connector ${VERSION}, run ${run}. label=${
        this.config.label ?? "(none)"
      }`,
      metadata: { path: cachePath },
    }));

    const res = await fetch("https://example.com/");
    const body = await res.text();
    updates.push(upsert({
      id: `${DOC_PREFIX}net`,
      title: `Sandbox net probe ${VERSION}`,
      content: `example.com answered ${res.status} with ${body.length} bytes`,
      metadata: { path: cachePath },
    }));

    if (this.config.probe_denied) {
      // Not granted before 1.2.0: the sync fails with a permission error.
      const denied = await fetch("https://httpbin.org/get");
      await denied.body?.cancel();
    }

    const folder = this.config.folder;
    if (typeof folder === "string" && folder !== "") {
      for await (const entry of Deno.readDir(folder)) {
        if (!entry.isFile || !entry.name.endsWith(".txt")) continue;
        const path = `${folder}/${entry.name}`;
        updates.push(upsert({
          id: `${DOC_PREFIX}file:${entry.name}`,
          title: `${entry.name} (${VERSION})`,
          content: (await Deno.readTextFile(path)).slice(0, 4096),
          metadata: { path },
        }));
      }
    }

    yield { updates, state: { run } };
  }
}
