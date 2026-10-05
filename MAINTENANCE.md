# Profile README

This repository is the GitHub profile README for [junguangjia](https://github.com/junguangjia). The page is `README.md`. It is not a website.

## Edit the copy

Change `content.json`, then regenerate. Do not draw SVG paths by hand. The script rewrites `README.md` and `readme/`.

```sh
python3 scripts/generate.py --font "$IBM_PLEX_MONO_OTF"
```

`$IBM_PLEX_MONO_OTF` is a directory outside this repository containing the official files:

- `IBMPlexMono-Regular.otf`
- `IBMPlexMono-Medium.otf`
- `IBMPlexMono-Bold.otf`

Install the generator dependency with `pip install -r requirements.txt` if `fontTools` is not already available.

## Font

The reference site at <https://ch3ny1.github.io/> declares `Berkeley Mono`, then `IBM Plex Mono`, then system monospace. It does not load a font file. In this environment the painted face was JetBrains Mono, because neither Berkeley Mono nor IBM Plex Mono is installed and `ui-monospace` resolved locally.

Berkeley Mono is a commercial face. It is not installed here, and there is no license that permits using it for these outlines. It is not the font in the assets.

The outlines are **IBM Plex Mono**, version 2.005, from the official IBM Plex release `@ibm/plex-mono@2.5.0` (<https://github.com/IBM/plex>). IBM Plex Mono is licensed under the SIL Open Font License 1.1. The license says it does not apply to a document created with the font. These SVGs are that document: glyph outlines, with no font file, no embedded font data, and no webfont. The font binaries stay on the machine that runs the generator and are not committed.

This is the reference's declared second face. It is not an exact match for Berkeley Mono.

Weights used: Regular, Medium, and Bold. `fsType` is 0.

## What the generator writes

- One desktop card, `readme/panel.svg`, and one narrow card, `readme/mobile/panel.svg`, selected with `<picture>` at a 720px viewport
- A static card for `prefers-reduced-motion`
- The same words again in the Text version at the bottom of `README.md`

The heading and introduction are one SVG, so that card has a single edge. The project list is separate pictures that share one pixel width, with no side stroke, so the phone does not step the border. Email and the website are real text links under that heading: the address can be selected and copied, and each address opens. Each project picture is a link. The text version repeats the same links.

The heading is `software · systems · machine learning`, with a separate blinking underscore in the next monospace cell. On a narrow screen it breaks before “machine learning” so the type stays readable. The heading types out like a command, then the indented lines appear in order, like a program printing. The cursor keeps its 1.1-second blink. Reduced motion, and any viewer where animation does not run, shows the finished text immediately. Website and email are indented code lines: `email > junguang.jia@columbia.edu` and `web > junguangjia.github.io`.

Badge labels are outlined from the same font. Logo paths are embedded in the card. `icons/NOTICE.md` records the Simple Icons CC0 sources. SQL is a generic database symbol. macOS is text only, without the Apple logo. The email and web lines are typed in the card; the text version links them.

## What the profile names

Languages: TypeScript, Swift, Python, Julia, R, SQL.

Web & Data: React, Next.js, PostgreSQL. ArtVenn's public web app depends on Next.js and React.

Platforms & Infrastructure: Web, macOS, Linux, Docker, GitHub Actions.

Linux stays because the public data work runs PostgreSQL and the search study in Linux containers. Ubuntu is not listed on its own: the clear Ubuntu-specific evidence is GitHub Actions' `ubuntu-latest` runner.

Not listed:

- iOS, iPadOS, visionOS, and watchOS. The ArtVenn Xcode project is still the multiplatform template.
- HarmonyOS. The public note says the DevEco project is not there yet.
- Windows and Android. No project evidence.
- Metal. Audio Transcribe enables it for arm64 whisper.cpp builds, and that repository says a compiler flag is not execution evidence.
- Nginx, Cloudflare, and Tencent Cloud. Nginx is not described as live. The gallery's Workers deploy script is not a verified public URL, and the photography project is not on the profile. Deployment notes say no cloud provider has been selected or provisioned.
- Convex, Tailwind, and shadcn/ui. They are not part of the verified inventory.

The visible product name is ArtVenn. The public repository path is `moya-inscriptions-web`. Moya and Yoyi are not used as the profile name.
