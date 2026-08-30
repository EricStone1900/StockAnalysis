import { readFile, writeFile } from 'node:fs/promises';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new globalThis.URL('../', import.meta.url));
const schema = JSON.parse(await readFile(`${root}schemas/domain-event-envelope.schema.json`, 'utf8'));
const required = new Set(schema.required);
const fields = Object.keys(schema.properties).map((name) => `  ${name}${required.has(name) ? '' : '?'}: ${name === 'schemaVersion' ? 'number' : name === 'payload' ? 'Record<string, unknown>' : 'string'};`).join('\n');
const ts = `// Generated from schemas/domain-event-envelope.schema.json. Do not edit.\nexport interface DomainEventEnvelope {\n${fields}\n}\n`;
const python = `# Generated from schemas/domain-event-envelope.schema.json. Do not edit.\nfrom typing import Any\nfrom pydantic import BaseModel\n\nclass DomainEventEnvelope(BaseModel):\n${Object.keys(schema.properties).map((name) => `    ${name}: ${name === 'schemaVersion' ? 'int' : name === 'payload' ? 'dict[str, Any]' : 'str'}${required.has(name) ? '' : ' | None = None'}`).join('\n')}\n`;
const outputs = [[`${root}src/generated/domain-event-envelope.ts`, ts], [`${root}generated/domain_event_envelope.py`, python]];
const check = process.argv.includes('--check');
for (const [path, content] of outputs) {
  const existing = await readFile(path, 'utf8').catch(() => '');
  if (check && existing !== content) throw new Error(`Generated contract drift: ${path}`);
  if (!check) await writeFile(path, content);
}
