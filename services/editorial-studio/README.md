# Editorial Studio local server

Requires Node.js 24 or newer in the managed cloud environment (for native environment-proxy support). No npm installation is needed.

```sh
cd /workspace/Notion
NODE_USE_ENV_PROXY=1 node services/editorial-studio/server.mjs
```

The server serves the repository and opens `editorial-studio.html` at its root. Default bind address: `127.0.0.1:8787`. Set `PORT` if needed. Keep the default loopback bind for personal use; this is a development server, not a multiuser production service.

## Actual image generation

Provide `STUDIO_IMAGE_API_KEY` securely in the server environment, then restart the server. Use the environment settings secret binding with destination `api.openai.com` in the managed cloud environment; `OPENAI_*` secret target names are reserved there. Existing local setups may continue to use `OPENAI_API_KEY` as a fallback; `STUDIO_IMAGE_API_KEY` takes precedence. Never put a key in the browser or tracked files. Optional `OPENAI_IMAGE_MODEL` defaults to `gpt-image-1`. The key must have image model access and billing. HTTPS access to `api.openai.com` must be allowed by the execution environment; the server uses inherited proxy/trust configuration supported by Node. With Node 24, launch with `NODE_USE_ENV_PROXY=1` when HTTP(S)_PROXY is supplied. Do not disable TLS verification.

Without a key, uploads and composition planning remain usable; the generation endpoint returns an explicit 503 and never fabricates photographs. Actual API generation incurs provider charges: 10 separate high-quality image requests per reference, up to 3 references. The frontend should show this before submitting.

`POST /api/studio/generate` accepts JSON with `identity.face`, `identity.body`, and `references[]`, each containing a JPG/PNG/WebP `dataUrl` and optional `name`. Each reference has a distinct `id`; `shots[]` contains exactly 10 records per reference with distinct `id`, `referenceId`, `pose`, `gaze`, `framing`, and optional `prompt`. Other fields: `mode` (`editorial`, `magazine`, `campaign`, `advertising`, `wedding`), `aspectRatio`, `brief`, and `layers[]` (`label`, `x`, `y`, `scale`, `rotation`). Videos must be converted to a selected still frame by the client; the image API does not receive the entire video.

Response: `202 {jobId}`. Poll `GET /api/studio/jobs/:id` for shot progress and JPEG `dataUrl` results. `DELETE` that path cancels pending work and aborts active requests; already submitted requests may still be billed. `GET /api/studio/status` reports key presence without revealing credentials; it does not verify provider authorization or billing. There are two concurrent image requests and at most two unfinished jobs. Jobs and images are kept in server memory for up to 30 minutes after completion and disappear on restart; download results promptly. The server also bounds retained results to four completed jobs/128MB and evicts the oldest jobs when needed. One job accepts at most 96MB of base64 output. Uploaded identity/reference files are released after completion. Nothing is written to the repository by the server.

The prompt asks the model to preserve facial identity and body proportions, reinterpret the reference mood with new clothing/accessories and compositions, and vary poses/gaze across the 10 cuts. Exact identity, anatomy, pose control, and photographic realism are not guaranteed; review results. Canvas layer positions guide the prompt as rough composition intent rather than pixel-accurate placement. The provider returns portrait 1024×1536 or square 1024×1024 for the UI’s options. The browser center-crops completed images to the exact selected 3:4, 4:5 or 1:1 ratio and exports JPEG; cropping can remove edge details. This creates images, not video output.

Use only model/reference files you are authorized to use. Files are sent to the selected image provider only when generation is submitted. For deployment, add authenticated sessions and per-user authorization, durable private storage, stronger cost quotas, a job queue and a reverse proxy with upload limits before exposing the service publicly. Current cross-origin checks do not replace authentication.

```sh
node --test services/editorial-studio/server.test.mjs
```

Tests use an in-memory mock image provider and do not call or bill the real API.

## Browser regression checks

With the local server running, execute `python tests/editorial-studio-browser.py` in a Python environment with Playwright installed. The test uses system Chromium at `/usr/bin/chromium` and mock API responses; no real image-generation calls are made. Override `STUDIO_URL` for a different local port. The default UI contains AI-created example photography in `assets/editorial-studio/`; these are labeled as examples, not user-specific generated results. The bundled DM Sans font retains its OFL license beside the font.

## Reusable model reference sheet

`POST /api/studio/model-sheet` creates **one paid landscape image edit** containing a single reusable reference board. The route uses the same key, same-origin check, rate limit, two-request concurrency, cancellation and temporary-memory retention as editorial jobs. It returns `202 {jobId}` and uses the existing `GET`/`DELETE /api/studio/jobs/:id` API. The completed job has `kind: "model-sheet"` and one JPEG result in `shots[0].dataUrl`; its native size is 1536×1024. Do not crop this multi-panel board to a portrait ratio.

Request shape:

```json
{
  "profile": {
    "id": "model-01",
    "name": "My model",
    "notes": "Features to preserve",
    "hair": "Keep original hairline and hairstyle",
    "eyes": "Keep eye shape and spacing",
    "skin": "Keep natural skin texture",
    "bodyNotes": "Keep body build and shoulder width"
  },
  "photos": [
    {"id": "face", "role": "face", "primary": true, "name": "front.jpg", "dataUrl": "data:image/jpeg;base64,..."},
    {"id": "body", "role": "body", "name": "full-body.jpg", "dataUrl": "data:image/jpeg;base64,..."},
    {"id": "side", "role": "side", "name": "side.jpg", "dataUrl": "data:image/jpeg;base64,..."}
  ],
  "expressionCount": 8
}
```

Use 2–10 real model photographs; each accepts JPG/PNG/WebP up to 6MB, and the complete JSON body must stay within 64MB. Exactly one `face` photo must be marked `primary: true`. At least one `body` photo must show the full body. Optional roles are `side`, `back`, and `extra`. Model photo IDs must be distinct. Select 6, 7 or 8 expressions. The first image sent to the provider is always the selected authoritative face, the second is the primary or first full-body photo, and remaining originals follow. Profile fields contain user-supplied directions, not automatically measured or verified facial geometry.

The generation prompt prioritizes facial consistency, aligned front/profile/back views, natural expressions and layout in that order. It requests a large reference face, equal-scale three-view body lineup, 6–8 expressions, eye/lip/skin details and a compact observed-color palette on a restrained neutral board. If a side or back photo is missing, that view is an **inferred reconstruction**, not verified evidence. Even with multiple originals, generative models cannot guarantee fixed biometric proportions, perfectly matched expression panels or identical identity in every later image. Review the board against the original face and full-body anchors before approving it.

To reuse an approved board in the existing `POST /api/studio/generate` flow, add:

```json
{
  "identityProfile": {"id": "model-01", "name": "My model", "sheetApproved": true, "notes": "Preserve the approved identity"},
  "identitySheet": {"name": "approved-model-sheet.jpg", "dataUrl": "data:image/jpeg;base64,..."},
  "supportingPhotos": [{"name": "side.jpg", "role": "side", "dataUrl": "data:image/jpeg;base64,..."}]
}
```

Continue including `identity.face`, `identity.body`, references, and 10 shot directions per reference. An `identitySheet` requires explicit `identityProfile.sheetApproved: true`; claiming approval without the actual sheet is rejected. Up to eight supporting original photographs are accepted, and the standard editorial request remains limited to 32MB total. Every shot receives the original authoritative face first, full-body anchor second, approved sheet third, its mood reference fourth, and optional additional originals after that. Without an approved sheet, the previous three-image contract still works. The prompt keeps identity/hair/build constraints separate from styling inspiration and never treats the sheet as a wardrobe reference.

Model source images and sheets are sent to the provider only when paid generation is requested. Server-side copies remain temporary and are released after the job finishes. Reusable browser model kits should preserve the selected originals and approved sheet together; export/import such a kit locally to reuse the same evidence across sessions. A user approval is an artistic review, not an automated biometric verification or a provider identity guarantee.

## Development validation without image API charges

`POST /api/studio/preview` exports the exact prompt and ordered originals for a sheet or editorial shot without requiring an API key or calling the image provider. It creates no generation job and returns no generated image. The payload is `{kind: "model-sheet" | "editorial", payload: <the existing model-sheet or editorial JSON>}`. Sheet requests retain the 64MB upload limit; editorial requests retain the 32MB limit. The same source validators, prompt builders, provider sizes and image-order helper are shared with paid generation. Existing same-origin protections also apply to this endpoint.

The response contains `billable: false`, configured `model`, `requestedQuality: "high"`, instructions, profile ID/revision, a deterministic `sourceFingerprint`, an `inputs` dictionary, and `shots`. Each dictionary item has an opaque `id`, dictionary `index`, `role`, `name`, image `dataUrl`, and SHA-256 checksum. Each shot has `prompt`, native `size` and ordered `inputIds`. Attach the originals in **that shot's `inputIds` order**, numbering those attachments from 1. Dictionary indices are not provider image positions when several mood references are present. Images appear only once in the dictionary, even when reused across 10 or 30 shots. The preview response uses `Cache-Control: no-store`; it is not persisted or logged by the server.

Use the exported prompt and originals in ChatGPT's image-generation interface, subject to the account's plan and usage limits, then bring a result back into the development UI for manual comparison/approval. This can evaluate the requested look and face-consistency behavior while exercising source preparation and result handling without image API charges. ChatGPT and the site's configured API may use different models or processing, so manually imported results **do not verify this API's image quality, latency or billable cost**. Mock UI tests validate application behavior and must never be reported as evidence of photographic realism. Final production-engine quality and cost still require a real, limited API run when authorized.
