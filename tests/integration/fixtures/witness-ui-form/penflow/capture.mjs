/** Measure this finite form directly; no contract or expected-tree input. */
import { writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { randomUUID } from "node:crypto";
import { pathToFileURL } from "node:url";
const [candidate, output, packagePath] = process.argv.slice(2);
const { chromium } = createRequire(packagePath)("@playwright/test");
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto(pathToFileURL(`${candidate}/index.html`).href);
  const monitor = await page.evaluateHandle(() => {
    let submissions = 0;
    const events = [];
    for (const type of ["input", "click", "submit", "invalid"]) {
      document.addEventListener(type, event => {
        if (type === "submit") submissions++;
        const target = event.submitter ?? event.target.closest("[data-action]") ?? event.target;
        events.push({ type, trusted: event.isTrusted,
          action_id: target.dataset.action ?? null, semantic_id: target.dataset.semanticId ?? null });
      }, true);
    }
    return { read: () => ({ submissions, events: [...events] }) };
  });
  const observe = () => page.evaluate(monitor => {
    const observed = monitor.read();
    const main = document.querySelector("main");
    const origin = main?.getBoundingClientRect() ?? { x: 0, y: 0 };
    const visible = node => { const r = node.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && getComputedStyle(node).visibility !== "hidden"; };
    const unmapped = [...document.querySelectorAll('button,input,select,textarea,a[href],[role="button"],[role="link"],[role="checkbox"],[role="radio"],[role="textbox"],[tabindex],[onclick],[contenteditable="true"]')]
      .filter(node => visible(node) && !node.dataset.semanticId).map(node => node.outerHTML);
    const nodes = [...document.querySelectorAll("[data-semantic-id]")].map(node => {
      const rect = node.getBoundingClientRect(), style = getComputedStyle(node);
      const roleMap = { button: "button", link: "link", textbox: "input", spinbutton: "input",
        combobox: "select", checkbox: "checkbox", radio: "radio", img: "image", status: "text", heading: "text" };
      const role = node.hasAttribute("role") ? roleMap[node.getAttribute("role")] :
        node === main ? "screen" : node.tagName === "INPUT" ?
        (["checkbox", "radio"].includes(node.type) ? node.type : "input") :
        node.tagName === "TEXTAREA" ? "input" : node.tagName === "SELECT" ? "select" :
        node.tagName === "IMG" ? "image" : node.tagName === "A" && node.hasAttribute("href") ? "link" :
        node.tagName === "BUTTON" ? "button" : node.children.length ? "container" : "text";
      if (!role) throw new Error("Unsupported actual role");
      const context = Object.fromEntries(["binding", "entity", "action", "testId"].filter(key => node.dataset[key])
        .map(key => [key === "testId" ? "test_id" : key, node.dataset[key]]));
      if (node.dataset.testid) context.test_id = node.dataset.testid;
      let painted = node;
      while (painted.parentElement && ["transparent", "rgba(0, 0, 0, 0)"].includes(getComputedStyle(painted).backgroundColor)) painted = painted.parentElement;
      const visual = { fill: role === "text" ? style.color : getComputedStyle(painted).backgroundColor,
        fontFamily: style.fontFamily, fontSize: parseFloat(style.fontSize), fontWeight: style.fontWeight,
        padding: [style.paddingTop, style.paddingRight, style.paddingBottom, style.paddingLeft].map(parseFloat) };
      if (style.display === "flex") Object.assign(visual, { layout: style.flexDirection === "column" ? "vertical" : "horizontal",
        gap: parseFloat(style.gap) || 0, alignItems: style.alignItems });
      if (parseFloat(style.borderTopWidth)) Object.assign(visual, { stroke: style.borderTopColor,
        strokeWidth: parseFloat(style.borderTopWidth), strokeAlignment: "inner" });
      return { id: node.dataset.semanticId, semantic_id: node.dataset.semanticId,
        parent_semantic_id: node.parentElement?.closest("[data-semantic-id]")?.dataset.semanticId ?? null,
        tag: node.tagName.toLowerCase(), role, context, visual,
        text: node.children.length ? null : node.textContent, value: node.value ?? null,
        required: node.required ?? null, visible: visible(node), enabled: !node.disabled,
        bbox: { x: rect.x - origin.x, y: rect.y - origin.y, width: rect.width, height: rect.height } };
    });
    const input = document.querySelector('[data-semantic-id="item-name"]');
    const success = document.querySelector('[data-semantic-id="success"]');
    return { url: location.href, actor_id: main?.dataset.actor ?? null,
      screen_id: main?.dataset.screen ?? null, state: main?.dataset.state ?? null,
      viewport: { width: innerWidth, height: innerHeight }, unmapped, nodes,
      submissions: observed.submissions, events: observed.events,
      properties: { name_validity: input.validity.valid ? "valid" : "invalid",
        submissions: observed.submissions, success_text: success.textContent, success_visible: visible(success) } };
  }, monitor);
  const before = await observe();
  await page.locator('[data-semantic-id="submit-item"]').click();
  const invalid = await observe();
  await page.locator('[data-semantic-id="item-name"]').fill("Atelier du jeudi");
  const edited = await observe();
  await page.locator('[data-semantic-id="submit-item"]').click();
  const valid = await observe();
  await writeFile(output, JSON.stringify({ kind: "livespec-witness-browser-capture", version: 1,
    source_kind: "runtime-capture", surface: "web", session_id: randomUUID(), scenario_id: "required-item-form",
    captured_at: new Date().toISOString(), browser_version: browser.version(), before, invalid, edited, valid }, null, 2));
} finally { await browser.close(); }
