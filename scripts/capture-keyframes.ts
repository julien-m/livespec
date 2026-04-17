#!/usr/bin/env ts-node
// @spec FR-019: Capture keyframes at 0%, 50%, 100% — .specs/features/010-visual-testing-complete/spec.md#fr-019
// @spec FR-020: Save to baselines/animations/[feature]/[component]-[percent].png — spec.md#fr-020
// @spec FR-022: Output YAML metadata with duration, easing, keyframe percentages — spec.md#fr-022
//
// Usage:
//   npx ts-node scripts/capture-keyframes.ts --component modal --feature dashboard --trigger '[data-testid="open-modal"]' --duration 300 --url http://localhost:3000/dashboard
//   npx tsx scripts/capture-keyframes.ts --component modal --feature dashboard --url http://localhost:3000

import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

interface CaptureConfig {
  component: string;
  feature: string;
  trigger?: string;
  target?: string;
  durationMs: number;
  easing: string;
  url: string;
  outDir: string;
}

function parseArgs(): CaptureConfig {
  const args = process.argv.slice(2);
  const get = (flag: string, defaultVal?: string): string => {
    const idx = args.indexOf(flag);
    if (idx !== -1 && args[idx + 1]) return args[idx + 1];
    if (defaultVal !== undefined) return defaultVal;
    throw new Error(`Missing required argument: ${flag}`);
  };

  const component = get('--component');
  const feature = get('--feature');
  const url = get('--url');
  const durationMs = parseInt(get('--duration', '300'), 10);

  return {
    component,
    feature,
    trigger: get('--trigger', ''),
    target: get('--target', ''),
    durationMs,
    easing: get('--easing', 'ease-in-out'),
    url,
    outDir: get('--out-dir', `baselines/animations/${feature}`),
  };
}

async function captureKeyframes(config: CaptureConfig): Promise<void> {
  const { component, feature, trigger, target, durationMs, easing, url, outDir } = config;

  // Ensure output directory exists
  mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log(`Navigating to ${url}...`);
  await page.goto(url);
  await page.waitForLoadState('networkidle');

  const locator = target ? page.locator(target) : page;
  const capturedFiles: string[] = [];

  // Keyframe 0%: initial state (before animation)
  const kf0Path = join(outDir, `${component}-kf-0pct.png`);
  await (locator as any).screenshot({ path: kf0Path, animations: 'allow' });
  capturedFiles.push(kf0Path);
  console.log(`[OK] Keyframe 0%: ${kf0Path}`);

  // Trigger animation if trigger selector provided
  if (trigger) {
    await page.locator(trigger).click();
    console.log(`Triggered: ${trigger}`);

    // @spec FR-021: waitForTimeout at 50% keyframe — spec.md#fr-021
    await page.waitForTimeout(durationMs * 0.5);

    // Keyframe 50%: mid-transition
    const kf50Path = join(outDir, `${component}-kf-50pct.png`);
    await (locator as any).screenshot({ path: kf50Path, animations: 'allow' });
    capturedFiles.push(kf50Path);
    console.log(`[OK] Keyframe 50%: ${kf50Path}`);

    // Wait for remaining duration
    await page.waitForTimeout(durationMs * 0.5);

    // Keyframe 100%: final state
    const kf100Path = join(outDir, `${component}-kf-100pct.png`);
    await (locator as any).screenshot({ path: kf100Path, animations: 'allow' });
    capturedFiles.push(kf100Path);
    console.log(`[OK] Keyframe 100%: ${kf100Path}`);
  } else {
    console.log('No --trigger provided. Captured keyframe 0% only (resting state).');
    console.log('Provide --trigger to capture mid-transition and final-state keyframes.');
  }

  await browser.close();

  // @spec FR-022: Output YAML metadata — spec.md#fr-022
  const metaPath = join(outDir, `${component}.keyframes.yml`);
  const meta = `# Keyframe capture metadata — ${component}
component: ${component}
feature: ${feature}
duration_ms: ${durationMs}
easing: ${easing}
keyframe_percentages: [0, 50, 100]
captured_date: ${new Date().toISOString().split('T')[0]}
trigger: "${trigger || ''}"
target: "${target || ''}"
files:
${capturedFiles.map(f => `  - ${f}`).join('\n')}
tolerance: 0.08
`;
  writeFileSync(metaPath, meta);
  console.log(`[OK] Metadata: ${metaPath}`);
  console.log(`\nDone. Captured ${capturedFiles.length} keyframe(s) to ${outDir}`);
}

captureKeyframes(parseArgs()).catch(err => {
  console.error('capture-keyframes error:', err.message);
  process.exit(1);
});
