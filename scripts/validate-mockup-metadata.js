#!/usr/bin/env node
// LiveSpec traceability anchors
// @spec(AC-002)
// @spec(FR-002)

// @spec FR-002: Validate mockup baseline metadata — .specs/features/010-visual-testing-complete/spec.md#fr-002
// Usage:
//   node scripts/validate-mockup-metadata.js [directory]
//   node scripts/validate-mockup-metadata.js baselines/mockups/ --fix

import { existsSync, readdirSync, readFileSync, writeFileSync } from 'fs';
import { join, basename, extname } from 'path';

// @spec AC-002: Required fields in .meta.yml — spec.md#ac-002
const REQUIRED_FIELDS = [
  'figma_url',
  'artboard_name',
  'exported_date',
  'designer_name',
  'resolution',
  'tolerance',
];

const STUB_META_TEMPLATE = (pngName) => `type: mockup
figma_url: https://figma.com/file/REPLACE_ME
artboard_name: REPLACE_ME
component: ${basename(pngName, extname(pngName))}
exported_date: ${new Date().toISOString().split('T')[0]}
designer_name: REPLACE_ME
resolution: 2x
tolerance: 0.02
last_updated: ${new Date().toISOString().split('T')[0]}
invalidate_on:
  - figma_mockup_change
  - designer_approval_revoked
`;

function parseYamlFields(content) {
  const fields = {};
  for (const line of content.split('\n')) {
    const match = line.match(/^(\w+):\s*(.+)$/);
    if (match) {
      fields[match[1].trim()] = match[2].trim();
    }
  }
  return fields;
}

function collectPngFiles(dir) {
  const pngFiles = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      pngFiles.push(...collectPngFiles(fullPath));
      continue;
    }
    if (extname(entry.name).toLowerCase() === '.png') {
      pngFiles.push(fullPath);
    }
  }
  return pngFiles;
}

function validateDirectory(dir, fix) {
  if (!existsSync(dir)) {
    console.error(`Directory not found: ${dir}`);
    process.exit(1);
  }

  const pngFiles = collectPngFiles(dir);

  if (pngFiles.length === 0) {
    console.log(`No PNG files found in ${dir}`);
    process.exit(0);
  }

  let errors = 0;
  let warnings = 0;
  let fixed = 0;

  for (const pngPath of pngFiles) {
    const metaPath = pngPath.replace(/\.png$/i, '.meta.yml');
    const png = basename(pngPath);

    if (!existsSync(metaPath)) {
      if (fix) {
        writeFileSync(metaPath, STUB_META_TEMPLATE(png));
        console.log(`[CREATED] ${metaPath} (stub — fill in REPLACE_ME values)`);
        fixed++;
      } else {
        console.error(`[ERROR] Missing metadata file: ${metaPath}`);
        errors++;
      }
      continue;
    }

    const content = readFileSync(metaPath, 'utf-8');
    const fields = parseYamlFields(content);

    const missing = REQUIRED_FIELDS.filter(f => !fields[f]);
    if (missing.length > 0) {
      console.error(`[ERROR] ${metaPath}: missing required fields: ${missing.join(', ')}`);
      errors++;
    } else {
      const hasPlaceholders = Object.values(fields).some(v => v.includes('REPLACE_ME'));
      if (hasPlaceholders) {
        console.warn(`[WARN] ${metaPath}: contains unfilled REPLACE_ME placeholders`);
        warnings++;
      } else {
        console.log(`[OK] ${metaPath}`);
      }
    }
  }

  console.log(`\nSummary: ${pngFiles.length} PNG(s), ${errors} error(s), ${warnings} warning(s)${fix ? `, ${fixed} stub(s) created` : ''}`);

  if (errors > 0) {
    console.error('\nFix: run with --fix to create stub .meta.yml files for missing metadata');
    process.exit(1);
  }
  process.exit(0);
}

// Parse CLI args
const args = process.argv.slice(2);
const fix = args.includes('--fix');
const dir = args.find(a => !a.startsWith('--')) || 'baselines/mockups/';

validateDirectory(dir, fix);
