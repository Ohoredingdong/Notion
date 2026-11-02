# Lossless preview decoder

`fflate-gunzip-0.8.2.min.js` contains only the browser `gunzipSync` entry from
fflate 0.8.2, bundled with esbuild 0.25.5. Its complete MIT license is included
both in the bundle's opening comment and in `fflate-0.8.2.LICENSE`.

This file is embedded only when a compact delivery exceeds the existing 1 MiB
budget. Normal project builds do not need fflate or esbuild installed: they read
this vendored file and use Python's standard `gzip` module. Browsers do not fetch
a decoder, create workers, or require `DecompressionStream`.

Reproduce the decoder outside the repository using an external tool directory:

```sh
npm install --prefix "$KITCHEN_VENDOR_TOOLS" --no-save --no-package-lock --ignore-scripts fflate@0.8.2 esbuild@0.25.5
```

Create an entry file in that directory containing:

```js
export {gunzipSync} from './node_modules/fflate/esm/browser.js';
```

Bundle it with the installed esbuild executable using:

```sh
esbuild ENTRY.mjs --bundle --minify --platform=browser --target=es2018 --format=iife --global-name=KitchenPackedDecoder --legal-comments=inline --outfile=OUTPUT.js
```

Prepend a `/*! ... */` comment containing the fflate version and full MIT license.
The checked-in bundle's SHA256 is
`924da5f88cb34410cf580a2ede9705c5369a511cbe6bf8dd6425829aa54a8ed5`.

`pack_document` writes deterministic gzip/base64 or HTML-safe gzip/base85 plus original UTF-8 byte count
and SHA256 metadata. `unpack_document` validates that count and digest for build,
review and verification tooling. The browser decoder checks the byte count,
then restores the original HTML after the envelope document finishes parsing.
It keeps the same browsing context, origin and iframe sandbox. No inventory,
record, storage-key, image-resolution or input-document bytes are rewritten.

The Base85 envelope uses RFC1924 digits with `&<>` replaced one-to-one by `.,/`. It carries exactly the same gzip bytes, supports partial groups, and requires no extra runtime library. Both codecs are supported by `unpack_document` and the embedded browser bootstrap.
