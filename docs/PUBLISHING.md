# Hosting and publishing this local repository

No remote repository has been created. The bundle contains a local `main` branch
and the preserved initial snapshot plus the NGISE revision; the source ZIP contains the working tree without
`.git`. GitHub connection, account selection, visibility, and licensing remain
owner decisions. Do not upload private review reports or access tokens.

## Restore Git history from the bundle

Download `MobiShard_NGISE2026_Repository.bundle` beside your desired parent directory:

```bash
git clone MobiShard_NGISE2026_Repository.bundle mobishard
cd mobishard
# Cloning a bundle sets origin to the local bundle. Remove that local origin
# before adding a hosting service; it is not a GitHub remote.
git remote remove origin
git status
```

The initial commit uses the neutral identity `Repository Assembly
<repository-assembly@example.invalid>`, not a forged author signature. Configure
your own Git name and email for subsequent commits. The local NGISE snapshot tag is
`v0.2.0-ngise2026`, with `v0.1.0` retained; it has not been published or archived as a DOI release.

## Start instead from the ZIP

Extract `MobiShard_NGISE2026_Repository.zip` and enter `mobishard/`. Then initialize a new
history using your configured Git identity:

```bash
git init -b main
git add .
git commit -m "Add MobiShard manuscript and reproducibility artifact"
```

## Create a private GitHub repository with GitHub CLI

After installing GitHub CLI and signing in on your own machine:

```bash
gh auth login
gh repo create mobishard --private --source=. --remote=origin --push
```

Omitting an owner creates the repository for the authenticated account. Supply
`OWNER/mobishard` only after choosing the appropriate account or organization.
Use a different name if it already exists. These commands create and upload
content; they have **not** been executed by this repository assembly.

The private default avoids making manuscript/source content publicly available
before you have reviewed permissions and venue anonymity requirements. Changing
it to public is a separate decision, not required for local reproduction.

## Before public release

- Confirm author approval, affiliations, institutional/IP obligations, and the
  license for code, data, model, figures, and manuscript. `LICENSE.md` currently
  records that no project-wide license was selected; no MIT/Apache/CC license was
  granted on the authors' behalf.
- Review manuscript distribution and anonymity requirements. This package includes
  named authors and source attribution.
- Verify the bibliography qualifications and current NGISE declarations and figure description.
- Run `python scripts/run_checks.py` and `python scripts/build_paper.py` on your
  machine, inspect the logs, and keep new trial data in a separate directory.
- Set the actual remote URL and, after any real release/archive, the resulting
  version identifiers in `CITATION.cff`. Do not add a placeholder DOI or acceptance
  statement to the manuscript.
- Exclude local credentials, detector reports, private correspondence, and unrelated
  draft papers. `.gitignore` is a convenience, not a comprehensive secrets audit.

The provided GitHub Actions workflow runs verification and a small integration
study, not the full performance campaign. Workflow definitions are present, but
no hosted CI result or badge is claimed.

## Provider documentation consulted for the scaffolding

- GitHub CLI repository creation: https://cli.github.com/manual/gh_repo_create
- GitHub citation files: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files
- Python setup action: https://github.com/actions/setup-python
- Checkout action releases: https://github.com/actions/checkout/releases
