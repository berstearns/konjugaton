# Release — public-safe clone → from-scratch build → deploy

konjugaton's equivalent of app7's release leg
([`app7-dev-workflow.md`](../p/minimal-android-apps/app7-dev-workflow.md) steps 4–5,
condensed in app7's `llm-agent-release-instruction.md`). This is the runbook for
shipping a release **the safe way**: never deploy from your dirty working tree —
deploy from a verified, secret-free clone built from scratch. The four surfaces
and the leao remote itself are documented in [`DEV-WORKFLOW.md`](DEV-WORKFLOW.md);
this file is only the *convert → e2e → deploy* leg that `DEV-WORKFLOW.md` points to.

## TL;DR

```bash
# (a) ONE-TIME per release — export a public-safe clone (scans for secrets, refuses to leak)
scripts/convert-to-public.sh                       # → ../public-konjugaton-<TS>/

# (b) build FROM that clone, from scratch, and upload to leao (binary gated by binary-smoke)
scripts/release-e2e.sh ../public-konjugaton-<TS> my-feature            # binary only
scripts/release-e2e.sh ../public-konjugaton-<TS> my-feature --with-apk # + Android APK
```

End result: artifacts at `ber:leao-bernardo/linguas/konjugaton/release/`, named
`<RUN_TS>-<feature>-linux` (the Nuitka binary) and, with `--with-apk`,
`<RUN_TS>-<feature>-release.apk`.

## How konjugaton differs from app7 (read this first)

app7's whole pipeline exists to **separate secrets from shippable code**: its
private dev folders carry a real `.env` (backend URL, queue, 8 Android signing
vars), real JKS keystores, and `server-config.yaml`. The conversion strips all
of that to placeholders before anything goes public.

**konjugaton has none of it.** No `.env`, no keystores, no API keys; the Android
`build.gradle.kts` has **no `signingConfig`** (release APKs are debug-signed /
minified). The only env vars are `KONJUGATON_HOME` / `KONJUGATON_USER` /
`XDG_STATE_HOME` — path overrides, not secrets. So konjugaton is **already
public-safe**, and this pipeline is inverted accordingly:

| app7 step | konjugaton equivalent |
|---|---|
| strip real `.env` → `.env.template` | scaffold `.env.template` (all keys optional) |
| keystores → text stubs | **conditional** — fires only if signing is ever added |
| `server-config.yaml` → placeholders | n/a (no backend) |
| bundled JSON → `[]` | n/a (the taxonomy *is* the product; it ships) |
| inject secrets in e2e clone | none to inject — clone builds as-is |
| **(new)** | a **secret-scan gate** that refuses to export if a secret ever appears |

The strip/inject steps are kept as **`skip (not present)` branches** (exactly
app7's idiom), so the day konjugaton grows a real secret — a signed-release
keystore, a sync backend, a TTS/LLM key — the pipeline already templates and
strips it with no rewrite.

## Inputs

| Input | How to determine |
|---|---|
| `<feature>` | A kebab label for this release; baked into the artifact filename (default `latest`). |
| `<public-folder>` | Output of `convert-to-public.sh`. `release-e2e.sh` auto-picks the newest `../public-konjugaton-*` if omitted. |
| `--with-apk`? | Pass it only if you want the Android APK uploaded too (needs `ANDROID_HOME` + JDK 17). |

## Prerequisites

- `uv`, `just`, `rclone` on PATH. `rclone listremotes` must show `ber:`.
- `--with-apk` additionally needs `ANDROID_HOME` (the SDK) and JDK 17.
- Network to the `ber:` remote (and to GitHub the first time `uv` resolves deps).

## Step-by-step

### 1. Convert → public-safe clone (one-time per release)

```bash
scripts/convert-to-public.sh                 # → ../public-konjugaton-<TS>/
# or pin the destination:
scripts/convert-to-public.sh /path/to/public-konjugaton-myrel
```

What it does (10 steps, **mtime-asserted — the source working tree is never
modified**, any drift aborts with exit 99):

1. resolve paths; refuse if the destination exists (exit 4)
2. snapshot the source mtime manifest (volatile dirs excluded)
3. **secret-scan gate** — fails (exit 5) on any real `.env`, `*.keystore`/`*.jks`/`*.p12`/`*.pem`/`*.key`, or inline PEM private-key block
4. clean `rsync` export (drops `.venv`, `.git`, `dist`, `build`, caches, runtime state, `.env`)
5. install `.env.template` (konjugaton's optional knobs + forward-looking signing vars)
6. harden `.gitignore` (`.env`, `*.keystore`, `*.jks`, …)
7. **conditional** Android signing strip — `skip (not present)` today
8. install `PUBLIC.md` (the how-to-build-this note)
9. fresh `git init` + initial commit
10. final source-untouched check + banner

### 2. e2e — build from scratch + deploy

```bash
scripts/release-e2e.sh ../public-konjugaton-<TS> my-feature [--with-apk]
```

What it does (never touches your tree or the canonical clone):

1. `cp -R <public>/ <public>_e2e_<RUN_TS>/` (fresh ephemeral clone per run)
2. seed `.env` from `.env.template` if absent (konjugaton builds without one)
3. `uv venv` + `uv pip install -e ".[dev,build]" patchelf` — from scratch
4. `just deploy-leao <feature>` — **gated**: runs `binary-smoke` (clean-env
   self-check over all 660,120 coordinates) first, so a packaging-broken binary
   never reaches leao
5. `--with-apk`: `just deploy-leao-apk <feature>`
6. print the remote listing for this run

### 3. Verify + report

After step 2 exits 0, surface to the user:

```
binary: ber:leao-bernardo/linguas/konjugaton/release/<RUN_TS>-<feature>-linux
apk:    ber:leao-bernardo/linguas/konjugaton/release/<RUN_TS>-<feature>-release.apk   (if --with-apk)
```

### 4. Hand-off testing

```bash
REMOTE="ber:leao-bernardo/linguas/konjugaton/release"
rclone copyto "${REMOTE}/<RUN_TS>-<feature>-linux" /tmp/konjugaton && chmod +x /tmp/konjugaton
env -i /tmp/konjugaton selfcheck    # clean-env gate, now against the shipped copy
rclone copyto "${REMOTE}/<RUN_TS>-<feature>-release.apk" /tmp/konjugaton.apk
adb install -r /tmp/konjugaton.apk  # -r preserves filesDir/state.json (no DB to wipe)
```

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `convert-to-public.sh` exit 4 | destination already exists | `rm -rf` it, or pass a new dest path |
| `convert-to-public.sh` exit 5 (`secret would leak`) | a real `.env`/keystore/private key is in the tree | move it out (or `.gitignore` + delete from the working dir), then re-run — **this is the gate doing its job** |
| `convert-to-public.sh` exit 99 (`source modified`) | something wrote to the working tree mid-run | investigate; the script protects the source — should never happen during a normal release |
| `release-e2e.sh` aborts in `just deploy-leao` | the `binary-smoke` gate failed | fix the Nuitka bundling regression (see [`DEV-WORKFLOW.md`](DEV-WORKFLOW.md) §2); the gate refuses to ship an unverified binary |
| `rclone copyto` 401/403 | `ber:` token expired | `rclone config reconnect ber:` (interactive) |
| `--with-apk` fails before compiling | `ANDROID_HOME` unset / JDK ≠ 17 | set the SDK + use JDK 17, or drop `--with-apk` |

## Hard rules

- **Never deploy from the working tree.** Always go through `convert-to-public.sh`
  → `release-e2e.sh`. The clean-env gate runs inside the e2e clone.
- **Never commit `.env` or key material** to a public clone. The scan gate +
  `.gitignore` enforce it; don't paste secrets into commits or PR bodies.
- **The taxonomy ships; secrets don't.** Unlike app7 (which stubs bundled JSON),
  konjugaton's `_data/*.yaml` *is* the product and is meant to be public.
- **Keep the conditional strip branches.** When konjugaton gains a real secret,
  wire it into `convert-to-public.sh` (a new conditional step) and `.env.template`
  — don't bolt on a parallel mechanism.

## Reference files

- [`scripts/convert-to-public.sh`](scripts/convert-to-public.sh) — public-safe export (10 steps, mtime-asserted, secret-scan gate)
- [`scripts/release-e2e.sh`](scripts/release-e2e.sh) — fresh clone → install → gated build → deploy
- [`DEV-WORKFLOW.md`](DEV-WORKFLOW.md) — the four surfaces + the leao remote
- [`justfile`](justfile) — `deploy-leao{,-apk,-all}`, `binary-smoke`, `leao-list`
- app7 originals: `~/p/minimal-android-apps/{convert-dev-to-public.sh,e2e.sh,llm-agent-release-instruction.md}`
