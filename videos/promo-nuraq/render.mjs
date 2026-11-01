#!/usr/bin/env node
/**
 * Rendu du spot Nuraq image par image avec Chromium (Playwright), puis assemblage avec ffmpeg.
 *
 *   node render.mjs                         # les deux formats → nuraq-spot-9x16.mp4 et nuraq-spot-16x9.mp4
 *   node render.mjs --format 16x9           # un seul format
 *   node render.mjs --stills 1.5,6.4,11.6   # images de contrôle PNG dans controle/
 *
 * Variables utiles : PLAYWRIGHT_MODULE (chemin du module playwright), JOBS (pages en parallèle).
 */
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import os from "node:os";

const HERE = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const pwPath = process.env.PLAYWRIGHT_MODULE || "/opt/node22/lib/node_modules/playwright";
const { chromium } = require(existsSync(pwPath) ? pwPath : "playwright");

const FPS = 30;
const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : def;
};
const formats = opt("format") ? [opt("format")] : ["9x16", "16x9"];
const stills = opt("stills");
const jobs = Number(process.env.JOBS || Math.max(1, Math.min(4, os.cpus().length - 1)));

const SIZE = { "9x16": [1080, 1920], "16x9": [1920, 1080] };

async function openPage(browser, format) {
  const [w, h] = SIZE[format];
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const url = pathToFileURL(join(HERE, "spot", "index.html")).href + `?format=${format}`;
  await page.goto(url);
  await page.evaluate(() => window.READY);
  return page;
}

async function renderStills(format) {
  const browser = await chromium.launch();
  const page = await openPage(browser, format);
  const dir = join(HERE, "controle");
  mkdirSync(dir, { recursive: true });
  for (const v of stills.split(",")) {
    const t = Number(v);
    await page.evaluate((t) => window.seek(t), t);
    const path = join(dir, `${format}-t${t.toFixed(2).padStart(5, "0")}.png`);
    await page.screenshot({ path });
    console.log(path);
  }
  await browser.close();
}

async function renderVideo(format) {
  const browser = await chromium.launch();
  const probe = await openPage(browser, format);
  const duration = await probe.evaluate(() => window.DURATION);
  await probe.close();
  const total = Math.round(duration * FPS);
  const dir = join(HERE, ".frames", format);
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
  let next = 0;
  let done = 0;
  const worker = async () => {
    const page = await openPage(browser, format);
    while (next < total) {
      const f = next++;
      await page.evaluate((t) => window.seek(t), f / FPS);
      await page.screenshot({ path: join(dir, `f${String(f).padStart(5, "0")}.jpg`), type: "jpeg", quality: 95 });
      done++;
      if (done % 60 === 0) console.log(`${format} : ${done}/${total}`);
    }
    await page.close();
  };
  await Promise.all(Array.from({ length: jobs }, worker));
  await browser.close();

  const audio = join(HERE, "son", "nuraq-spot.wav");
  const out = join(HERE, `nuraq-spot-${format}.mp4`);
  const ff = ["-y", "-v", "error", "-framerate", String(FPS), "-i", join(dir, "f%05d.jpg")];
  if (existsSync(audio)) ff.push("-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest");
  ff.push("-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out);
  await new Promise((res, rej) => {
    const p = spawn("ffmpeg", ff, { stdio: "inherit" });
    p.on("exit", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg ${c}`))));
  });
  rmSync(dir, { recursive: true, force: true });
  console.log(out);
}

for (const f of formats) {
  if (stills) await renderStills(f);
  else await renderVideo(f);
}
