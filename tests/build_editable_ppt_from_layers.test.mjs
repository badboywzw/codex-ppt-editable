import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import {
  parseArgs,
  requireArg,
  slideSize,
  parseCanvas,
  resolveAssetPath,
  sortByLayerOrder,
  visibleStyleValue,
  collectTextFillViolations,
  slidesFromTextSpec,
  assetPosition,
  textPosition,
  normalizePptxColor,
  pptxScale,
  toPptxPosition,
  findPageDir,
  buildWithPptxGen,
} from "../scripts/build_editable_ppt_from_layers.mjs";

const ONE_BY_ONE_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg==",
  "base64",
);

describe("build_editable_ppt_from_layers helpers", () => {
  it("parses CLI arguments and slide sizes", () => {
    const args = parseArgs(["--layers-root", "/tmp/layers", "--fail-on-text-fill", "-h"]);
    assert.equal(args["layers-root"], "/tmp/layers");
    assert.equal(args["fail-on-text-fill"], true);
    assert.equal(args.help, true);
    assert.equal(requireArg(args, "layers-root"), "/tmp/layers");
    assert.throws(() => requireArg(args, "missing"), /Missing required --missing/);

    assert.deepEqual(slideSize("1920x1080"), { width: 1920, height: 1080 });
    assert.deepEqual(slideSize(), { width: 960, height: 540 });
    assert.throws(() => slideSize("bad"), /Expected --slide-size/);

    assert.deepEqual(parseCanvas([1920, 1080]), [1920, 1080]);
    assert.deepEqual(parseCanvas("1920x1080"), [1920, 1080]);
    assert.deepEqual(parseCanvas({ width: 960, height: 540 }), [960, 540]);
    assert.equal(parseCanvas(null), null);
  });

  it("blocks path traversal in resolveAssetPath", () => {
    const base = "/tmp/slides/slide-01";
    assert.equal(resolveAssetPath(base, "card.png"), path.resolve(base, "card.png"));
    assert.throws(() => resolveAssetPath(base, "../secret.png"), /escapes/);
    assert.throws(() => resolveAssetPath(base, "/etc/passwd"), /escapes/);
    assert.throws(() => resolveAssetPath(base, ""), /Invalid asset file/);
  });

  it("scales asset and text coordinates from source canvas to target slideSize", () => {
    const size = { width: 960, height: 540 };
    const asset = { file: "a.png", position: [960, 540, 480, 270] };
    assert.deepEqual(assetPosition(asset, size, [1920, 1080]), {
      left: 480,
      top: 270,
      width: 240,
      height: 135,
    });

    const objAsset = {
      file: "b.png",
      position: { x: 192, y: 108, w: 384, h: 216 },
      canvas: "1920x1080",
    };
    assert.deepEqual(assetPosition(objAsset, size), {
      left: 96,
      top: 54,
      width: 192,
      height: 108,
    });

    const textItem = { text: "Title", x: 200, y: 100, w: 800, h: 120 };
    assert.deepEqual(textPosition(textItem, size, [1920, 1080]), {
      left: 100,
      top: 50,
      width: 400,
      height: 60,
    });
  });

  it("sorts layers stably by zIndex or order", () => {
    const items = [
      { name: "top", zIndex: 10 },
      { name: "base-1" },
      { name: "base-2" },
      { name: "back", order: -5 },
    ];
    assert.deepEqual(
      sortByLayerOrder(items).map((x) => x.name),
      ["back", "base-1", "base-2", "top"],
    );
  });

  it("detects visible text box fills and lines", () => {
    assert.equal(visibleStyleValue("transparent"), false);
    assert.equal(visibleStyleValue("#00000000"), false);
    assert.equal(visibleStyleValue("#FF006E"), true);

    const specs = slidesFromTextSpec({
      canvas: [1920, 1080],
      slides: [
        {
          slide: 1,
          texts: [
            { name: "clean", text: "OK", fill: "transparent" },
            { name: "bad", text: "Patched", fill: "#112233" },
          ],
        },
      ],
    });
    const violations = collectTextFillViolations(specs);
    assert.equal(violations.length, 1);
    assert.equal(violations[0].name, "bad");
  });

  it("normalizes colors and PPTX scale", () => {
    assert.equal(normalizePptxColor("#FFE600"), "FFE600");
    assert.equal(normalizePptxColor(""), "333333");
    const scale = pptxScale({ width: 960, height: 540 });
    assert.deepEqual(
      toPptxPosition({ left: 480, top: 270, width: 240, height: 135 }, scale),
      { x: 5, y: 2.8125, w: 2.5, h: 1.40625 },
    );
  });

  it("builds an end-to-end editable PPTX with pptxgenjs backend", async () => {
    const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "codex-ppt-test-"));
    try {
      const layersRoot = path.join(tmpDir, "visual-layers");
      const slideDir = path.join(layersRoot, "slide-01");
      await fs.mkdir(slideDir, { recursive: true });
      await fs.writeFile(path.join(slideDir, "hero.png"), ONE_BY_ONE_PNG);
      await fs.writeFile(
        path.join(slideDir, "manifest.json"),
        JSON.stringify({
          canvas: [1920, 1080],
          background: "#000000",
          assets: [{ file: "hero.png", position: [100, 100, 600, 400], zIndex: 1 }],
        }),
        "utf8",
      );

      const found = await findPageDir(layersRoot, 1);
      assert.equal(found, slideDir);

      const textSpec = {
        background: "#FFFFFF",
        canvas: [1920, 1080],
        slides: [
          {
            slide: 1,
            background: "#000000",
            texts: [
              {
                name: "title",
                text: "Codex PPT v0.3",
                x: 160,
                y: 120,
                w: 800,
                h: 90,
                size: 36,
                bold: true,
                italic: true,
                underline: true,
                color: "#FFE600",
              },
            ],
          },
        ],
      };
      const slideSpecs = slidesFromTextSpec(textSpec);
      const outPptx = path.join(tmpDir, "final", "test.editable.pptx");
      const workspace = path.join(tmpDir, "workspace");
      const previewDir = path.join(workspace, "preview");
      const layoutDir = path.join(workspace, "layout");
      const manifestOut = path.join(workspace, "build-manifest.json");

      await buildWithPptxGen({
        layersRoot,
        out: outPptx,
        workspace,
        previewDir,
        layoutDir,
        manifestOut,
        size: { width: 960, height: 540 },
        preserveTextFill: false,
        textSpec,
        slideSpecs,
        textFillViolations: [],
        textJson: path.join(tmpDir, "text-layer.json"),
      });

      const stat = await fs.stat(outPptx);
      assert.ok(stat.size > 0);
      const buildManifest = JSON.parse(await fs.readFile(manifestOut, "utf8"));
      assert.equal(buildManifest.slideCount, 1);
      assert.equal(buildManifest.slides[0].visualLayerCount, 1);
      assert.equal(buildManifest.slides[0].textCount, 1);
    } finally {
      await fs.rm(tmpDir, { recursive: true, force: true });
    }
  });
});
