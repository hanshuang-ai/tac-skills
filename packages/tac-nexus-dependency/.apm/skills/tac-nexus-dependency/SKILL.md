---
name: tac-nexus-dependency
version: 0.4.5
description: >
  Finds Android/Maven dependencies in a Nexus repository, resolves the latest
  version, lists available versions when there are multiple choices, and
  integrates the selected dependency into an Android Gradle project. Use when
  the user wants to add a dependency from Nexus by package name, inspect Nexus
  versions, or wire a Nexus Maven repository into an Android project.
---

# Nexus Android Dependency

Use this skill when the task is:

- add a dependency from a Nexus Maven repository into an Android project
- look up the latest version for a package in Nexus
- list all available versions before choosing one
- wire a Nexus repository into Gradle and update module dependencies

This skill is built for the common Android Gradle flow:

1. resolve the package coordinates from Nexus
2. determine the newest version
3. if there are multiple versions, show them explicitly
4. integrate the chosen version into the Android project
5. verify the repository and dependency wiring

## Required Inputs

Collect or infer these values before running the scripts:

- `base_url`: Nexus base URL, for example `https://nexus.example.com`
- `repository`: Nexus Maven repository name, for example `maven-releases` or `maven-public`
- package identifier:
  - preferred: `group:artifact`
  - fallback: artifact name only, such as `okhttp`
- Android target module, for example `app`

Optional:

- `NEXUS_USERNAME` / `NEXUS_PASSWORD` environment variables for private repos
- exact alias/version key to use in `libs.versions.toml`
- custom Gradle configuration such as `api`, `kapt`, `testImplementation`

For the current environment, the known Nexus base URL is:

- `http://10.1.120.33:50382/`

## Workflow

### Step 1: Resolve and inspect versions

Prefer the bundled script:

```powershell
$env:NEXUS_USERNAME = "<your nexus username>"
$env:NEXUS_PASSWORD = "<your nexus password>"

python tac-skills/tac-nexus-dependency/scripts/find_nexus_versions.py `
  --base-url http://10.1.120.33:50382 `
  --repository maven-public `
  --package com.squareup.okhttp3:okhttp `
  --list-all `
  --allow-insecure
```

Behavior:

- if the package is an exact `group:artifact`, the script tries `maven-metadata.xml` first
- if only an artifact name is provided, the script searches Nexus and groups matches by coordinate
- it prints the latest version
- if multiple versions exist, it prints the version list
- if multiple naming styles exist in the version list, it also groups versions by naming style
- if multiple coordinates match the same artifact name, it prints all coordinate candidates instead of guessing

#### Naming Style Rule

If the returned versions contain multiple naming styles, do not continue directly to integration.

You must first turn the style choice into a user question and wait for the answer.

Use a short numbered choice, for example:

```text
这个包存在多种版本命名风格，请先选择要接入哪一条版本线：
1. WT2.5_TINNOVE_Design-*  当前最新: WT2.5_TINNOVE_Design-2.5.0.hz
2. WT2.0G_mainLineGroup01-*  当前最新: WT2.0G_mainLineGroup01-2.0.0.fx_260420_1905
3. J90K-*  当前最新: J90K-1.0.0.es
```

Only after the user selects one style may you choose the latest version inside that style and continue.

Practical detection rule:

- treat the version prefix before the numeric core such as `-2.5.0`, `-1.0.0`, `-2.0.0` as the naming style
- examples:
  - `WT2.5_TINNOVE_Design-2.5.0.hz` -> `WT2.5_TINNOVE_Design`
  - `WT2.0G_mainLineGroup01-2.0.0.fx_260420_1905` -> `WT2.0G_mainLineGroup01`
  - `J90K-1.0.0.es` -> `J90K`

Rules:

- do not silently pick a coordinate when the artifact name maps to multiple groups
- do not silently pick a version when the user asked to review version options
- do not silently pick a cross-style latest version when multiple naming styles are present
- if Nexus access fails because of sandbox or network restrictions, request escalation and rerun

### Step 2: Integrate into Android Gradle

After the user confirms the version, prefer the bundled integration script:

```powershell
python tac-skills/tac-nexus-dependency/scripts/add_nexus_dependency.py `
  --project-root . `
  --module app `
  --repository-url http://10.1.120.33:50382/repository/maven-public/ `
  --dependency com.squareup.okhttp3:okhttp:4.12.0 `
  --credentials-mode env `
  --dry-run
```

Optional flags:

- `--configuration api`
- `--alias okhttp`
- `--version-key okhttp`
- `--credentials-mode env`
- `--dry-run`

Behavior:

- adds the Nexus Maven repository to `dependencyResolutionManagement.repositories`
- if `gradle/libs.versions.toml` exists, adds version + library alias there
- updates the target module `build.gradle(.kts)` to reference the dependency
- if no version catalog exists, falls back to a raw Gradle dependency string

## Supported Auth Modes

Preferred:

- lookup script:
  - `NEXUS_USERNAME` / `NEXUS_PASSWORD`
  - or `--username` / `--password`
- Gradle integration:
  - `--credentials-mode env`
  - read credentials from Gradle properties `nexusUsername` / `nexusPassword`
  - or environment variables `NEXUS_USERNAME` / `NEXUS_PASSWORD`

Other common Nexus auth modes:

- anonymous read-only access
- user token or PAT mapped to HTTP Basic auth
- reverse-proxy SSO in front of Nexus

This skill does not hardcode secrets into Gradle or repo files.

### Step 3: Verification

Always verify after integration.

Minimum verification:

1. confirm the repository URL exists in `settings.gradle(.kts)`
2. confirm the dependency entry exists in `gradle/libs.versions.toml` or the module build file
3. confirm the target module references the dependency in the expected configuration

Preferred verification if the environment allows Gradle execution:

```powershell
.\gradlew.bat :app:dependencies
```

If the user asks for a real integration in the current repo, make the code edits instead of only printing commands.

## Project-Specific Guidance

When the current project already uses `gradle/libs.versions.toml`, prefer:

1. add a version key under `[versions]`
2. add a library alias under `[libraries]`
3. use `libs.<alias accessor>` in the module dependency block

Do not switch the project away from its current dependency management style.

## Bundled Scripts

- `scripts/find_nexus_versions.py`
  - resolves coordinates
  - lists versions
  - highlights the newest version
- `scripts/add_nexus_dependency.py`
  - adds the Nexus repository to Gradle settings
  - updates the version catalog when present
  - wires the dependency into a target Android module

## Decision Rules

- Exact `group:artifact` beats artifact-name fuzzy matching.
- If multiple coordinates are returned, show them and wait for confirmation.
- If multiple versions exist, list them before integrating when the user asked for version visibility.
- If multiple naming styles are detected, ask the user to choose the target style before selecting a version.
- Prefer the smallest edit set that matches the existing Gradle structure.
- Do not modify auth files. Use environment variables or Gradle properties for Nexus credentials.
