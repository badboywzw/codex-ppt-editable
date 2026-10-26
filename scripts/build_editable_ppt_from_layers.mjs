#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { readJson, writeJson } from "./lib/json_io.mjs";

const require = createRequire(import.meta.url);

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === "-h") {
      args.help = true;
      continue;
    }
    if (!key.startsWith("--")) throw new Error(`Unexpected argument: ${key}`);
    const next = argv[i + 1];
    if (!next || next.startsWith("-")) {
      args[key.slice(2)] = true;
    } else {
      args[key.slice(2)] = next;
      i += 1;
    }
  }
  return args;
}

function printHelp() {
  console.log(`Usage:
  node scripts/build_editable_ppt_from_layers.mjs \\
    --layers-root /path/to/visual-layers \\
    --text-json /path/to/text-layer.json \\
    --out /path/to/editable.pptx \\
    [--workspace /path/to/workspace] \\
    [--preview-dir /path/to/preview] \\
    [--layout-dir /path/to/layout] \\
    [--slide-size 960x540] \\
    [--backend auto|artifact|pptxgenjs] \\
    [--preserve-text-fill] \\
    [--fail-on-text-fill]

Notes:
  - backend=auto tries the Codex Presentations artifact runtime first, then falls back to pptxgenjs.
  - backend=artifact renders PPTX, preview PNGs, and layout JSON through the Codex Presentations runtime.
  - backend=pptxgenjs generates an editable PPTX without preview rendering; run npm install in the skill folder first.
  - Set PRESENTATIONS_ARTIFACT_UTILS to artifact_tool_utils.mjs when using backend=artifact outside the bundled Codex environment.
`);
}

function requireArg(args, key) {
  if (!args[key]) throw new Error(`Missing required --${key}`);
  return String(args[key]);
}

function slideSize(value) {
  const match = String(value || "960x540").match(/^(\d+)[xX](\d+)$/);
  if (!match) throw new Error(`Expected --slide-size WIDTHxHEIGHT, got ${value}`);
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (width <= 0 || height <= 0) {
    throw new Error(`Expected positive --slide-size dimensions, got ${value}`);
  }
  return { width, height };
}

function parseCanvas(value) {
  if (!value) return null;
  if (Array.isArray(value) && value.length === 2) {
    const w = Number(value[0]);
    const h = Number(value[1]);
    if (w > 0 && h > 0) return [w, h];
  }
  if (typeof value === "string") {
    const match = value.trim().match(/^(\d+)[xX](\d+)$/);
    if (match) {
      const w = Number(match[1]);
      const h = Number(match[2]);
      if (w > 0 && h > 0) return [w, h];
    }
  }
  if (typeof value === "object" && !Array.isArray(value)) {
    const w = Number(value.width ?? value.w);
    const h = Number(value.height ?? value.h);
    if (w > 0 && h > 0) return [w, h];
  }
  return null;
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function resolveAssetPath(baseDir, file) {
  if (typeof file !== "string" || file.trim().length === 0) {
    throw new Error(`Invalid asset file entry in manifest: ${JSON.stringify(file)}`);
  }
  const resolvedBase = path.resolve(baseDir);
  const resolved = path.resolve(resolvedBase, file);
  const rel = path.relative(resolvedBase, resolved);
  if (rel === "" || rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`Asset path escapes its slide folder: ${file}`);
  }
  return resolved;
}

function isMissingPathError(error) {
  return error?.code === "ENOENT" || error?.code === "ENOTDIR";
}

function sortByLayerOrder(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item, idx) => ({
      item,
      idx,
      order: Number(item?.zIndex ?? item?.order ?? 0),
    }))
    .sort((a, b) => (a.order !== b.order ? a.order - b.order : a.idx - b.idx))
    .map((entry) => entry.item);
}

function visibleStyleValue(value) {
  if (value === undefined || value === null || value === false) return false;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    return !["", "none", "transparent", "#00000000", "rgba(0,0,0,0)"].includes(normalized);
  }
  if (typeof value === "object") {
    if ("fill" in value && visibleStyleValue(value.fill)) return Number(value.width ?? 1) !== 0;
    if ("color" in value && visibleStyleValue(value.color)) return true;
    return Object.values(value).some((entry) => visibleStyleValue(entry));
  }
  return Boolean(value);
}

function lineFillValue(value, transparent) {
  if (value && typeof value === "object") return value.fill || value.color || transparent;
  return value || transparent;
}

function lineWidthValue(item, preserveTextFill) {
  if (!preserveTextFill) return 0;
  if (!item.line) return 0;
  if (item.line && typeof item.line === "object" && item.line.width !== undefined) return Number(item.line.width);
  return Number(item.lineWidth ?? 1);
}

function hasVisibleTextBoxStyle(item) {
  return visibleStyleValue(item.fill) || visibleStyleValue(item.line);
}

function collectTextFillViolations(slideSpecs) {
  const violations = [];
  for (const slideSpec of slideSpecs) {
    slideSpec.texts.forEach((item, index) => {
      if (!hasVisibleTextBoxStyle(item)) return;
      violations.push({
        slide: slideSpec.slide,
        index: index + 1,
        name: item.name || `text-${index + 1}`,
        text: String(item.text ?? "").slice(0, 80),
        fill: item.fill ?? null,
        line: item.line ?? null,
      });
    });
  }
  return violations;
}

async function importUtils() {
  const explicit = process.env.PRESENTATIONS_ARTIFACT_UTILS;
  const candidates = [explicit].filter(Boolean);
  const presentationsRoot = path.join(os.homedir(), ".codex/plugins/cache/openai-primary-runtime/presentations");
  try {
    const entries = await fs.readdir(presentationsRoot, { withFileTypes: true });
    const versions = entries
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort()
      .reverse();
    for (const version of versions) {
      candidates.push(path.join(presentationsRoot, version, "skills/presentations/scripts/artifact_tool_utils.mjs"));
    }
  } catch (error) {
    if (!isMissingPathError(error)) throw error;
  }
  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
    } catch (error) {
      if (isMissingPathError(error)) continue;
      throw error;
    }
    try {
      return await import(pathToFileURL(candidate).href);
    } catch (error) {
      throw new Error(
        `Found Presentations artifact utils at ${candidate} but failed to import it: ${error?.message || error}`,
        { cause: error },
      );
    }
  }
  throw new Error("Could not locate Presentations artifact_tool_utils.mjs. Set PRESENTATIONS_ARTIFACT_UTILS.");
}

function isArtifactRuntimeMissing(error) {
  return String(error?.message || error || "").includes("Could not locate Presentations artifact_tool_utils.mjs");
}

function importPptxGen() {
  try {
    const mod = require("pptxgenjs");
    return mod.default || mod;
  } catch (error) {
    throw new Error(
      `Could not load pptxgenjs fallback backend. Run "npm install" in the codex-ppt skill folder first. Original error: ${error.message}`,
    );
  }
}

async function findPageDir(root, slideNo) {
  const names = [
    `第${pad(slideNo)}页`,
    `slide-${pad(slideNo)}`,
    `slide_${pad(slideNo)}`,
    pad(slideNo),
    String(slideNo),
  ];
  for (const name of names) {
    const dir = path.join(root, name);
    try {
      const stat = await fs.stat(dir);
      if (stat.isDirectory()) return dir;
    } catch (error) {
      if (isMissingPathError(error)) continue;
      throw error;
    }
  }
  throw new Error(`Could not find page folder for slide ${slideNo} under ${root}`);
}

function slidesFromTextSpec(spec) {
  if (!Array.isArray(spec.slides)) throw new Error("Text JSON must contain a slides array.");
  const deckCanvas = parseCanvas(spec.canvas || spec.sourceCanvas);
  return spec.slides.map((slide, index) => ({
    slide: Number(slide.slide ?? index + 1),
    background: slide.background || null,
    canvas: parseCanvas(slide.canvas || slide.sourceCanvas) || deckCanvas,
    route: slide.route || null,
    texts: Array.isArray(slide.texts) ? slide.texts : [],
  }));
}

function extractRawBox(item) {
  const pos = item?.position;
  if (Array.isArray(pos) && pos.length === 4) {
    return {
      left: Number(pos[0]),
      top: Number(pos[1]),
      width: Number(pos[2]),
      height: Number(pos[3]),
    };
  }
  if (pos && typeof pos === "object" && !Array.isArray(pos)) {
    const left = pos.left ?? pos.x;
    const top = pos.top ?? pos.y;
    const width = pos.width ?? pos.w;
    const height = pos.height ?? pos.h;
    if (left !== undefined && top !== undefined && width !== undefined && height !== undefined) {
      return { left: Number(left), top: Number(top), width: Number(width), height: Number(height) };
    }
  }
  const left = item?.x ?? item?.left;
  const top = item?.y ?? item?.top;
  const width = item?.w ?? item?.width;
  const height = item?.h ?? item?.height;
  if (left !== undefined && top !== undefined && width !== undefined && height !== undefined) {
    return { left: Number(left), top: Number(top), width: Number(width), height: Number(height) };
  }
  return null;
}

function scaleBoxToSize(box, size, canvas) {
  if (!canvas) {
    return {
      left: box.left,
      top: box.top,
      width: Math.max(1, box.width),
      height: Math.max(1, box.height),
    };
  }
  const [canvasWidth, canvasHeight] = canvas;
  return {
    left: (box.left / canvasWidth) * size.width,
    top: (box.top / canvasHeight) * size.height,
    width: Math.max(1, (box.width / canvasWidth) * size.width),
    height: Math.max(1, (box.height / canvasHeight) * size.height),
  };
}

function assetPosition(asset, size, fallbackCanvas = null) {
  const box = extractRawBox(asset);
  if (!box) {
    return { left: 0, top: 0, width: size.width, height: size.height };
  }
  const canvas =
    parseCanvas(asset.canvas) ||
    parseCanvas(asset.sourceCanvas) ||
    parseCanvas(fallbackCanvas);
  return scaleBoxToSize(box, size, canvas);
}

function textPosition(item, size, fallbackCanvas = null) {
  const box = extractRawBox(item) || { left: 0, top: 0, width: 1, height: 1 };
  const canvas =
    parseCanvas(item?.canvas) ||
    parseCanvas(item?.sourceCanvas) ||
    parseCanvas(fallbackCanvas);
  return scaleBoxToSize(box, size, canvas);
}

function normalizePptxColor(value, fallback = "333333") {
  if (!value) return fallback;
  const text = String(value).trim();
  if (text.startsWith("#")) return text.slice(1).slice(0, 6) || fallback;
  return text.slice(0, 6) || fallback;
}

function pptxScale(size) {
  const width = 10;
  return {
    x: width / size.width,
    y: ((width * size.height) / size.width) / size.height,
    width,
    height: (width * size.height) / size.width,
  };
}

function toPptxPosition(position, scale) {
  return {
    x: Number(position.left) * scale.x,
    y: Number(position.top) * scale.y,
    w: Number(position.width) * scale.x,
    h: Number(position.height) * scale.y,
  };
}

async function addImageLayer(slide, artifactUtils, filePath, size, name, asset = {}, fallbackCanvas = null) {
  const image = slide.images.add({
    blob: await artifactUtils.readImageBlob(filePath),
    fit: asset.fit || "contain",
    alt: asset.alt || name,
    name,
  });
  image.position = assetPosition(asset, size, fallbackCanvas);
  return image;
}

function addTextBox(slide, item, index, options = {}) {
  const transparent = "#00000000";
  const preserveTextFill = Boolean(options.preserveTextFill);
  const size = options.size || { width: 960, height: 540 };
  const fallbackCanvas = options.canvas || null;
  const position = textPosition(item, size, fallbackCanvas);
  if (item.rotation !== undefined && item.rotation !== null) {
    position.rotation = Number(item.rotation);
  }
  const shape = slide.shapes.add({
    geometry: "rect",
    name: item.name || `text-${index}`,
    position,
    fill: preserveTextFill ? item.fill || transparent : transparent,
    line: {
      fill: preserveTextFill ? lineFillValue(item.line, transparent) : transparent,
      width: lineWidthValue(item, preserveTextFill),
    },
  });
  shape.text = String(item.text ?? "");
  shape.text.fontSize = Number(item.size ?? item.fontSize ?? 14);
  shape.text.typeface = item.typeface || item.fontFace || "PingFang SC";
  shape.text.color = item.color || "#333333";
  shape.text.bold = Boolean(item.bold);
  if (item.italic !== undefined) shape.text.italic = Boolean(item.italic);
  if (item.underline !== undefined) shape.text.underline = Boolean(item.underline);
  shape.text.alignment = item.align || "left";
  shape.text.verticalAlignment = item.valign || "top";
  shape.text.insets = item.insets || { left: 0, right: 0, top: 0, bottom: 0 };
  shape.text.wrap = item.wrap || "square";
  if (item.autoFit) shape.text.autoFit = item.autoFit;
  return shape;
}

function addTextBoxPptxGen(slide, item, index, scale, options = {}) {
  const preserveTextFill = Boolean(options.preserveTextFill);
  const size = options.size || { width: 960, height: 540 };
  const fallbackCanvas = options.canvas || null;
  const scaledBox = textPosition(item, size, fallbackCanvas);
  const position = toPptxPosition(scaledBox, scale);
  const pptxOptions = {
    ...position,
    name: item.name || `text-${index}`,
    margin: 0,
    fontFace: item.typeface || item.fontFace || "PingFang SC",
    fontSize: Number(item.size ?? item.fontSize ?? 14),
    color: normalizePptxColor(item.color),
    bold: Boolean(item.bold),
    italic: item.italic !== undefined ? Boolean(item.italic) : undefined,
    underline: item.underline ? { style: "sng" } : undefined,
    align: item.align || "left",
    valign: item.valign || "top",
    fit: item.autoFit === "shrink" ? "shrink" : undefined,
    rotate: item.rotation !== undefined && item.rotation !== null ? Number(item.rotation) : undefined,
    charSpacing: item.charSpacing ?? item.letterSpacing ?? undefined,
    lineSpacingMultiple: item.lineSpacingMultiple ?? undefined,
    transparency: item.transparency !== undefined
      ? Number(item.transparency)
      : (item.opacity !== undefined ? Math.round((1 - Number(item.opacity)) * 100) : undefined),
    bullet: item.bullet ? Boolean(item.bullet) : undefined,
    breakLine: false,
  };
  if (preserveTextFill && visibleStyleValue(item.fill)) {
    pptxOptions.fill = { color: normalizePptxColor(item.fill, "FFFFFF"), transparency: 0 };
  }
  if (preserveTextFill && visibleStyleValue(item.line)) {
    pptxOptions.line = {
      color: normalizePptxColor(lineFillValue(item.line, "#000000"), "000000"),
      width: lineWidthValue(item, true),
    };
  } else {
    pptxOptions.line = { color: "FFFFFF", transparency: 100 };
  }
  slide.addText(String(item.text ?? ""), pptxOptions);
}

async function loadVisualManifest(pageDir) {
  const manifestPath = path.join(pageDir, "manifest.json");
  const manifest = await readJson(manifestPath);
  const rawAssets = Array.isArray(manifest.assets) ? manifest.assets : [];
  const assets = sortByLayerOrder(rawAssets);
  const canvas = parseCanvas(manifest.canvas || manifest.sourceCanvas || manifest.slideSize);
  const background = manifest.background || null;
  return { manifest, assets, canvas, background };
}

async function addVisualLayers(slide, artifactUtils, pageDir, size, slideNo, fallbackCanvas = null) {
  const { assets, canvas } = await loadVisualManifest(pageDir);
  const effectiveCanvas = canvas || fallbackCanvas;
  for (const asset of assets) {
    const assetPath = resolveAssetPath(pageDir, asset.file);
    await addImageLayer(
      slide,
      artifactUtils,
      assetPath,
      size,
      asset.name || `slide-${pad(slideNo)}-${asset.file}`,
      asset,
      effectiveCanvas,
    );
  }
  return { count: assets.length, canvas: effectiveCanvas };
}

async function addVisualLayersPptxGen(slide, pageDir, size, slideNo, scale, fallbackCanvas = null) {
  const { assets, canvas, background } = await loadVisualManifest(pageDir);
  const effectiveCanvas = canvas || fallbackCanvas;
  for (const asset of assets) {
    const assetPath = resolveAssetPath(pageDir, asset.file);
    const position = assetPosition(asset, size, effectiveCanvas);
    const imgOpts = {
      path: assetPath,
      ...toPptxPosition(position, scale),
      altText: asset.name || `slide-${pad(slideNo)}-${asset.file}`,
    };
    if (asset.transparency !== undefined) {
      imgOpts.transparency = Number(asset.transparency);
    } else if (asset.opacity !== undefined) {
      imgOpts.transparency = Math.round((1 - Number(asset.opacity)) * 100);
    }
    if (asset.rotation !== undefined && asset.rotation !== null) {
      imgOpts.rotate = Number(asset.rotation);
    }
    slide.addImage(imgOpts);
  }
  return { count: assets.length, canvas: effectiveCanvas, background };
}

async function buildWithPptxGen({
  layersRoot,
  out,
  workspace,
  previewDir,
  layoutDir,
  manifestOut,
  size,
  preserveTextFill,
  textSpec,
  slideSpecs,
  textFillViolations,
  textJson,
}) {
  const PptxGenJS = importPptxGen();
  const pptx = new PptxGenJS();
  const scale = pptxScale(size);
  pptx.author = "Codex PPT";
  pptx.subject = "Editable PPTX generated from slide visual layers";
  pptx.title = "Codex PPT editable output";
  pptx.company = "Codex PPT";
  pptx.lang = "zh-CN";
  pptx.defineLayout({ name: "IMAGE_PPT_KING_CUSTOM", width: scale.width, height: scale.height });
  pptx.layout = "IMAGE_PPT_KING_CUSTOM";
  pptx.theme = {
    headFontFace: "PingFang SC",
    bodyFontFace: "PingFang SC",
    lang: "zh-CN",
  };

  const records = [];
  for (const slideSpec of slideSpecs) {
    const slide = pptx.addSlide();
    const pageDir = await findPageDir(layersRoot, slideSpec.slide);
    const {
      count: visualLayerCount,
      canvas: manifestCanvas,
      background: manifestBg,
    } = await addVisualLayersPptxGen(slide, pageDir, size, slideSpec.slide, scale, slideSpec.canvas);

    const slideBg = slideSpec.background || manifestBg || textSpec.background || "#F7F8F7";
    slide.background = { color: normalizePptxColor(slideBg, "F7F8F7") };

    const effectiveCanvas = slideSpec.canvas || manifestCanvas;
    const orderedTexts = sortByLayerOrder(slideSpec.texts);
    orderedTexts.forEach((textItem, index) =>
      addTextBoxPptxGen(slide, textItem, index + 1, scale, {
        preserveTextFill,
        size,
        canvas: effectiveCanvas,
      }),
    );
    records.push({
      slideNumber: slideSpec.slide,
      pageDir,
      visualLayerCount,
      textCount: orderedTexts.length,
    });
  }

  await fs.mkdir(path.dirname(out), { recursive: true });
  await pptx.writeFile({ fileName: out });
  const stat = await fs.stat(out);
  if (stat.size <= 0) throw new Error(`Empty PPTX exported: ${out}`);

  await fs.mkdir(previewDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });
  for (let i = 0; i < records.length; i += 1) {
    await writeJson(path.join(layoutDir, `slide-${pad(i + 1)}.layout.json`), {
      backend: "pptxgenjs",
      slide: records[i].slideNumber,
      note: "Layout JSON is a lightweight object summary. Pixel preview rendering requires backend=artifact.",
      pageDir: records[i].pageDir,
      visualLayerCount: records[i].visualLayerCount,
      textCount: records[i].textCount,
    });
  }

  const buildManifest = {
    output: out,
    bytes: stat.size,
    backend: "pptxgenjs",
    slideCount: records.length,
    slideSize: size,
    layersRoot,
    textJson,
    workspace,
    previewDir,
    layoutDir,
    previewPaths: [],
    previewNote: "backend=pptxgenjs does not render preview PNGs. Use backend=artifact in Codex Presentations runtime for previews.",
    textFillPolicy: preserveTextFill ? "preserve" : "strip",
    textFillViolationCount: textFillViolations.length,
    textFillViolations,
    slides: records,
  };
  await writeJson(manifestOut, buildManifest);
  console.log(JSON.stringify(buildManifest, null, 2));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }
  const layersRoot = path.resolve(requireArg(args, "layers-root"));
  const textJson = path.resolve(requireArg(args, "text-json"));
  const out = path.resolve(requireArg(args, "out"));
  const workspace = path.resolve(args.workspace || path.join(path.dirname(out), "codex-ppt-editable-workspace"));
  const previewDir = args["preview-dir"] ? path.resolve(args["preview-dir"]) : path.join(workspace, "preview");
  const layoutDir = args["layout-dir"] ? path.resolve(args["layout-dir"]) : path.join(workspace, "layout");
  const manifestOut = args.manifest ? path.resolve(args.manifest) : path.join(workspace, "build-manifest.json");
  const size = slideSize(args["slide-size"]);
  const preserveTextFill = Boolean(args["preserve-text-fill"]);
  const failOnTextFill = Boolean(args["fail-on-text-fill"]);
  const backend = String(args.backend || "auto");
  if (!["auto", "artifact", "pptxgenjs"].includes(backend)) {
    throw new Error(`Unsupported --backend ${backend}; expected auto, artifact, or pptxgenjs.`);
  }

  const textSpec = await readJson(textJson);
  const slideSpecs = slidesFromTextSpec(textSpec);
  const textFillViolations = collectTextFillViolations(slideSpecs);
  if (failOnTextFill && textFillViolations.length > 0) {
    throw new Error(`Text JSON contains ${textFillViolations.length} text boxes with fill/line. Remove them or build without --fail-on-text-fill.`);
  }

  let utils = null;
  if (backend !== "pptxgenjs") {
    try {
      utils = await importUtils();
    } catch (error) {
      if (backend === "artifact" || !isArtifactRuntimeMissing(error)) throw error;
    }
  }

  if (!utils) {
    await buildWithPptxGen({
      layersRoot,
      out,
      workspace,
      previewDir,
      layoutDir,
      manifestOut,
      size,
      preserveTextFill,
      textSpec,
      slideSpecs,
      textFillViolations,
      textJson,
    });
    return;
  }

  await utils.ensureArtifactToolWorkspace(workspace);
  const artifact = await utils.importArtifactTool(workspace);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize: size });
  const records = [];

  for (const slideSpec of slideSpecs) {
    const slide = presentation.slides.add();
    const pageDir = await findPageDir(layersRoot, slideSpec.slide);
    const { background: manifestBg, canvas: manifestCanvas } = await loadVisualManifest(pageDir);
    const slideBg = slideSpec.background || manifestBg || textSpec.background || "#F7F8F7";
    const bg = slide.shapes.add({
      geometry: "rect",
      name: `slide-${pad(slideSpec.slide)}-background`,
      position: { left: 0, top: 0, width: size.width, height: size.height },
      fill: slideBg,
      line: { fill: slideBg, width: 0 },
    });
    bg.text = "";
    const { count: visualLayerCount } = await addVisualLayers(
      slide,
      utils,
      pageDir,
      size,
      slideSpec.slide,
      slideSpec.canvas || manifestCanvas,
    );
    const effectiveCanvas = slideSpec.canvas || manifestCanvas;
    const orderedTexts = sortByLayerOrder(slideSpec.texts);
    orderedTexts.forEach((textItem, index) =>
      addTextBox(slide, textItem, index + 1, {
        preserveTextFill,
        size,
        canvas: effectiveCanvas,
      }),
    );
    records.push({
      slideNumber: slideSpec.slide,
      pageDir,
      visualLayerCount,
      textCount: orderedTexts.length,
      slideObject: slide,
    });
  }

  await fs.mkdir(path.dirname(out), { recursive: true });
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(out);
  const stat = await fs.stat(out);
  if (stat.size <= 0) throw new Error(`Empty PPTX exported: ${out}`);

  await fs.mkdir(previewDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });
  const previewPaths = [];
  for (let i = 0; i < records.length; i += 1) {
    const n = pad(i + 1);
    const previewPath = path.join(previewDir, `slide-${n}.png`);
    await utils.saveBlobToFile(await presentation.export({ slide: records[i].slideObject, format: "png", scale: 1 }), previewPath);
    previewPaths.push(previewPath);
    await utils.saveBlobToFile(await presentation.export({ slide: records[i].slideObject, format: "layout" }), path.join(layoutDir, `slide-${n}.layout.json`));
  }

  const buildManifest = {
    output: out,
    bytes: stat.size,
    backend: "artifact",
    slideCount: records.length,
    slideSize: size,
    layersRoot,
    textJson,
    previewDir,
    layoutDir,
    textFillPolicy: preserveTextFill ? "preserve" : "strip",
    textFillViolationCount: textFillViolations.length,
    textFillViolations,
    slides: records.map(({ slideNumber, pageDir, visualLayerCount, textCount }) => ({ slide: slideNumber, pageDir, visualLayerCount, textCount })),
    previewPaths,
  };
  await writeJson(manifestOut, buildManifest);
  console.log(JSON.stringify(buildManifest, null, 2));
}

const invokedDirectly = Boolean(process.argv[1]) && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedDirectly) {
  main().catch((error) => {
    console.error(error.stack || error.message || String(error));
    process.exit(1);
  });
}

export {
  parseArgs,
  requireArg,
  slideSize,
  parseCanvas,
  pad,
  resolveAssetPath,
  isMissingPathError,
  sortByLayerOrder,
  visibleStyleValue,
  lineFillValue,
  lineWidthValue,
  hasVisibleTextBoxStyle,
  collectTextFillViolations,
  importUtils,
  isArtifactRuntimeMissing,
  findPageDir,
  slidesFromTextSpec,
  assetPosition,
  textPosition,
  normalizePptxColor,
  pptxScale,
  toPptxPosition,
  addTextBox,
  addTextBoxPptxGen,
  buildWithPptxGen,
  main,
};
