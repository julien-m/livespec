#!/usr/bin/env node
// @spec FR-017: CI visual diff PR comment — .specs/features/010-visual-testing-complete/spec.md#fr-017
// Posts visual diff results to GitHub PR as a comment when visual tests fail in CI.
// Idempotent: updates existing comment if already present (marker: <!-- visual-diff-bot -->)

import { existsSync, readdirSync, statSync } from 'fs';
import { join, extname } from 'path';
import { execSync } from 'child_process';

const COMMENT_MARKER = '<!-- visual-diff-bot -->';

async function postPRComment(token, repo, prNumber, body) {
  const url = `https://api.github.com/repos/${repo}/issues/${prNumber}/comments`;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };

  // Check for existing comment to update (idempotent behavior)
  const listResponse = await fetch(url, { headers });
  if (!listResponse.ok) {
    console.warn(`Failed to list PR comments: ${listResponse.status}`);
    return;
  }
  const comments = await listResponse.json();
  const existing = comments.find(c => c.body && c.body.includes(COMMENT_MARKER));

  if (existing) {
    // Update existing comment
    const updateUrl = `https://api.github.com/repos/${repo}/issues/comments/${existing.id}`;
    const updateResponse = await fetch(updateUrl, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ body }),
    });
    if (!updateResponse.ok) {
      console.warn(`Failed to update PR comment: ${updateResponse.status}`);
    } else {
      console.log(`Updated visual diff comment on PR #${prNumber}`);
    }
  } else {
    // Create new comment
    const createResponse = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ body }),
    });
    if (!createResponse.ok) {
      console.warn(`Failed to create PR comment: ${createResponse.status}`);
    } else {
      console.log(`Posted visual diff comment on PR #${prNumber}`);
    }
  }
}

function findDiffImages(testResultsDir) {
  if (!existsSync(testResultsDir)) return [];
  const images = [];

  function walk(dir) {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      const stat = statSync(full);
      if (stat.isDirectory()) {
        walk(full);
      } else if (['.png', '.jpg', '.jpeg'].includes(extname(entry).toLowerCase())) {
        images.push(full);
      }
    }
  }

  walk(testResultsDir);
  return images;
}

async function main() {
  const token = process.env.GITHUB_TOKEN;
  const repo = process.env.REPO;
  const prNumber = process.env.PR_NUMBER;
  const project = process.env.PROJECT || 'unknown';
  const runId = process.env.RUN_ID || '';

  if (!token || !repo || !prNumber) {
    console.warn('Missing required env vars: GITHUB_TOKEN, REPO, PR_NUMBER. Skipping PR comment.');
    process.exit(0);
  }

  const testResultsDir = join(process.cwd(), 'test-results');
  const diffImages = findDiffImages(testResultsDir);

  // No-op if no diff images found
  if (diffImages.length === 0) {
    console.log('No visual diff images found. Skipping PR comment.');
    process.exit(0);
  }

  const artifactUrl = runId
    ? `https://github.com/${repo}/actions/runs/${runId}`
    : `https://github.com/${repo}/actions`;

  const imageList = diffImages
    .slice(0, 20) // cap at 20 images to avoid massive comments
    .map(p => `- \`${p.replace(process.cwd() + '/', '')}\``)
    .join('\n');

  const body = `${COMMENT_MARKER}
## Visual Test Failures — \`${project}\`

Visual tests detected rendering differences in the \`${project}\` configuration.

### Diff Images (${diffImages.length} file${diffImages.length !== 1 ? 's' : ''})

${imageList}${diffImages.length > 20 ? `\n\n_(and ${diffImages.length - 20} more)_` : ''}

### Review & Approve

1. **Download artifacts:** [View run artifacts](${artifactUrl}) → download \`visual-diff-${project}\`
2. **Review diffs:** Compare \`actual\`, \`expected\`, and \`diff\` PNGs
3. **If change is intentional:** Run \`npx playwright test --update-snapshots --project=${project}\` locally, commit updated baselines
4. **If change is a bug:** Fix the regression and push a new commit

> @designer — please review the diff images above and approve or reject the visual changes.

_Posted by visual-diff-bot · [Run ${runId}](${artifactUrl})_
`;

  await postPRComment(token, repo, prNumber, body);
}

main().catch(err => {
  console.error('visual-diff-pr-comment.js error:', err.message);
  // Non-blocking: exit 0 so CI doesn't fail due to comment script error
  process.exit(0);
});
