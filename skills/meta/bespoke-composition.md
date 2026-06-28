# Bespoke Composition (Atelier Mode)

Meta-skill for **hand-authoring a composition from scratch** instead of assembling stock
scene-types. This is the "hand-stitched every time" path: for hero pieces, every pixel of the
look is written fresh so no two videos share a visual language.

Read this whenever you've chosen **atelier mode** for a piece (see "When to use"). It does not
hand you components — it routes you to the *principles, engine mechanics, and tool wiring* you
need so that what you build is correct, and distinct.

> The single rule that governs everything below: **reuse engine knowledge, never creative
> components.** How Remotion resolves an asset is engine knowledge — reuse it freely. How a
> previous video looked is a creative decision — never reuse it.

## When to use this skill (authoring mode is a proposal decision)

OpenMontage now separates three orthogonal axes, all locked at proposal:

- `renderer_family` — creative grammar
- `render_runtime` — technical engine (remotion / hyperframes / ffmpeg)
- **`composition_mode`** — **templated** (assemble stock `cut.type` scenes) **vs. atelier** (hand-author)

Pick **atelier** by default for: marketing, launches, explainers that must impress, brand
pieces, anything single-deliverable where quality is the point. Pick **templated** for: batch
output, localization variants, quick drafts, low-stakes internal clips — places where reliable
sameness is fine and bespoke cost is unjustified. Present the choice to the user at proposal and
log it in `decision_log` (`category: "composition_mode"`), the same way you present runtime.

If atelier is chosen, the stock scene-type catalog, the `hyperframes-registry` blocks, fixtures,
and any finished component are **off-limits** — they are frozen looks and reintroduce sameness.

## The construction route

Author in this order. Each step routes you to existing knowledge — do not skip the first one.

### 1. Commit to an art direction *for this subject* — the divergence engine
Before writing any component, decide a visual language that fits **this** topic and no other.
Use the **`visual-style`** Layer 3 skill (CREATE mode) to lock: palette, type personality,
motion character, layout system, and **one signature device** unique to this piece. Difference
between videos is guaranteed here — not by withholding components, but by forcing a fresh
direction each time. Write it down (a short `art-direction.md` in the project) and build to it.

Ask yourself: *what visual metaphor belongs to this subject that I have not used before?* If the
answer resembles a past piece, you haven't found the direction yet.

### 2. Decide the motion language — principles, not presets
Reach for **principle** skills, never finished animations:
- **`framer-motion`** and **`lottie-bodymovin`** — Disney's 12 principles (anticipation, staging,
  follow-through, slow-in/out, arc, timing, exaggeration, appeal). Runtime-agnostic; apply the
  *principles* in your own Remotion `spring()`/`interpolate()` code.
- The HyperFrames `references/motion-principles.md` — easing as emotion, timing as weight.

### 3. Reach for a richer vocabulary only when the concept demands it
Most scenes are Remotion primitives. Escalate when the *idea* needs it, not by default:
`gsap-*` (kinetic typography via SplitText, shape morph via MorphSVG, curved motion via
MotionPath, line-draw via DrawSVG, custom easing), `threejs-*` (3D), `d3-viz` (data-driven
custom charts — build the chart by hand; do **not** drop in the stock `bar_chart`/`line_chart`),
`manim-*` (math), `canvas-procedural-animation` (particles/weather).

### 4. Get the engine mechanics right — the gotcha codex
This is the only place you "reuse": the engine's solved problems. These are facts about how
Remotion works, not looks. Study `.agents/skills/remotion-best-practices` (19 rule files:
timing, transitions, text-animations, transparent video, fonts, audio, sequencing, measuring
text). You may also read the stock components in `remotion-composer/src/components/` **as a
mechanics codex — to learn idioms, never to import or imitate a look.**

Recurring mechanics that bite if you don't know them:
- **Determinism**: no `Math.random()` / `Date.now()` per frame — use Remotion `random(seed)` or a
  seeded helper, or particles/easing flicker across the render.
- **Per-scene duration**: `useVideoConfig().durationInFrames` returns the *composition* length, not
  your scene's. Drive scene-local timing from a passed `durationInFrames`/`Sequence`, not the global.
- **Asset paths**: URLs and `staticFile()` (public/) work everywhere; **`<Audio>` rejects `file://`**
  (only `<OffthreadVideo>`/`<Img>` accept absolute `file://`). Put audio/video in a per-project
  public dir and reference via `staticFile`. Mirror the `resolveAsset` helper.
- **GSAP-in-Remotion**: use a `paused` timeline and `.seek(frame/fps)` — never `requestAnimationFrame`
  — so frames render deterministically.
- **Fonts**: `loadFont()` from `@remotion/google-fonts/<Name>` at module scope, once.

### 5. Render through the atelier path (project-local, throwaway)
Bespoke scenes are **throwaway and project-local** — they never enter the shared `src/` registry.

- Author under `remotion-composer/projects/<slug>/` (gitignored). It needs its own Remotion entry
  (`index.tsx` + a `Root` registering only this composition) so it reuses the composer's
  `node_modules` and stays out of the global `Root.tsx`. The entry MUST live under
  `remotion-composer/` for the bundler to resolve `remotion`.
- Keep media in a small per-project public dir and pass it as `public_dir` so renders don't copy
  the bloated shared `public/`.
- Render via `video_compose` `operation="render"` with:

```json
edit_decisions = {
  "render_runtime": "remotion",
  "composition_mode": "atelier",
  "bespoke": {
    "entry": "remotion-composer/projects/<slug>/index.tsx",
    "composition_id": "<id registered in that entry's Root>",
    "props_path": "<absolute path to props.json>",
    "public_dir": "<absolute path to the project's public dir>",
    "scale": 0.5,          // 0.5 for a fast draft; drop for the 1080p final
    "crf": 18,             // crisp final
    "concurrency": 8
  }
}
```

No `asset_manifest` or `cuts` are required in atelier mode — the composition owns its own assets.

## Guardrails so this doesn't backfire

- **Distinctness review (replaces conformance review).** Before final render, ask: *could this be
  any other product's video? Does it reuse a look I've made before?* If yes, the art direction
  failed — return to step 1. This is the inverse of "does it match the reference."
- **No silent fallback to stock.** "Keep it simple" applies to *mechanics* (a 10-line spring is
  fine), never to *design* (simple ≠ reaching for `text_card`). If you catch yourself adding a
  stock `cut.type` to a hero piece, stop.
- **Cost honesty.** Atelier costs more agent tokens and iteration than templated. Say so at proposal
  so the user opts in knowingly. Quality varies more without a stock baseline — mitigate with strong
  principle skills (above) and the distinctness review, not by reintroducing reuse.
- **Checkpoint cadence.** Follow `skills/meta/checkpoint-protocol.md`: present script + scene plan
  for approval BEFORE generating assets, then a footage/asset checkpoint, then a first-render
  checkpoint. Do not batch-generate ahead of sign-off.

## Worked precedent (for the *workflow*, not the look)

The first atelier piece was the Phantom Reach explainer (`projects/phantom-reach-explainer/`):
Playwright-captured app footage with a PII-blur layer → per-sentence TTS stitched with silence
beats → free Pixabay music → hand-authored Remotion scenes (custom intro, score-ring, agentic
flow, CTA) on a one-off violet theme. Study its **process** (capture → timing → props builder →
bespoke scenes → render). **Do not reproduce its visual language** — the next piece must look
nothing like it. That is the whole point.

See also: `skills/meta/animation-runtime-selector.md` (runtime + library routing),
`AGENT_GUIDE.md` → "Composition Authoring Mode".
