# Releasing Agent Eval Kit

Agent Eval Kit publishes versioned builds through GitHub Releases only. The project is not published to PyPI.

## Release identity

- GitHub owner: `ZhiweiZhang97`
- GitHub repository: `agent-eval-kit`
- Release workflow: `.github/workflows/release.yml`

The package version in `pyproject.toml` must exactly match the release tag with a leading `v`. For example, package version `0.5.0` must be released with tag `v0.5.0`.

## Release procedure

1. Confirm the default-branch CI is green.
2. Update the package version, changelog, citation metadata, and documentation.
3. Create and push the matching version tag:

   ```bash
   git checkout main
   git pull --ff-only
   git tag -a v0.5.0 -m "Agent Eval Kit v0.5.0"
   git push origin v0.5.0
   ```

4. The `Release` workflow will:
   - confirm the tagged commit is reachable from `main`,
   - verify the tag matches `pyproject.toml`,
   - build the source distribution and wheel,
   - run Twine metadata checks,
   - create a GitHub Release,
   - attach both build artifacts to the Release.

## Installation

Users can install directly from GitHub:

```bash
pip install "git+https://github.com/ZhiweiZhang97/agent-eval-kit.git@v0.5.0"
```

Or download the wheel from the GitHub Release and install it locally:

```bash
pip install agent_eval_kit-0.5.0-py3-none-any.whl
```

## Failure behavior

If the tag does not match the package version, or the tag points to a commit that is not reachable from `main`, the workflow stops before creating a Release.

Changes to `.github/workflows/release.yml` should be reviewed as release-sensitive changes because the workflow has permission to create GitHub Releases.
