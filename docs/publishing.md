# Releasing Agent Eval Kit

Agent Eval Kit publishes versioned builds through GitHub Releases only. The project is not published to PyPI.

## Release identity

- GitHub owner: `ZhiweiZhang97`
- GitHub repository: `agent-eval-kit`
- Release workflow: `.github/workflows/release.yml`

The package version in `pyproject.toml` must exactly match the release version.

## Recommended: release from GitHub Actions

1. Confirm the default-branch CI is green.
2. Open **Actions → Release → Run workflow**.
3. Enter the version without a leading `v`, for example `0.5.0`.
4. Run the workflow.

The workflow verifies that the requested version matches `pyproject.toml`, confirms the release commit is on `main`, creates the corresponding annotated Git tag, builds the source distribution and wheel, runs Twine metadata checks, creates the GitHub Release, and attaches both artifacts.

## Alternative: release by pushing a tag

You can also create the version tag locally:

```bash
git checkout main
git pull --ff-only
git tag -a v0.5.0 -m "Agent Eval Kit v0.5.0"
git push origin v0.5.0
```

A pushed `v*` tag triggers the same build and GitHub Release pipeline.

## Installation

Users can install directly from a release tag:

```bash
pip install "git+https://github.com/ZhiweiZhang97/agent-eval-kit.git@v0.5.0"
```

Or download the wheel from the GitHub Release and install it locally:

```bash
pip install agent_eval_kit-0.5.0-py3-none-any.whl
```

## Safety checks

The workflow refuses a release when:

- the requested/tagged version does not match `pyproject.toml`,
- the release commit is not reachable from `main`,
- a manual release tries to create a tag that already exists,
- package build or Twine metadata validation fails.

Changes to `.github/workflows/release.yml` should be reviewed as release-sensitive because the workflow can create tags and GitHub Releases.
