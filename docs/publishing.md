# Publishing Agent Eval Kit

Agent Eval Kit uses GitHub Actions and PyPI Trusted Publishing. No long-lived PyPI API token is required.

## Release identity

For this repository:

- PyPI project: `agent-eval-kit`
- GitHub owner: `ZhiweiZhang97`
- GitHub repository: `agent-eval-kit`
- Trusted Publisher workflow: `release.yml`
- GitHub environment: `pypi`

The package version in `pyproject.toml` must exactly match the release tag with a leading `v`. For example, package version `0.5.0` must be released with tag `v0.5.0`.

## First publication

Before creating the first release tag, sign in to PyPI and add a pending GitHub Trusted Publisher for the identity above.

A pending publisher is appropriate when the PyPI project does not exist yet. The first successful trusted publication creates the project automatically.

The exact PyPI project name must match the `project.name` value in `pyproject.toml`.

## GitHub environment

The release workflow uses the GitHub Actions environment named `pypi`.

Repository administrators should configure protection rules for that environment when appropriate, such as restricting deployment branches/tags or requiring a maintainer approval for publishing.

## Release procedure

1. Confirm the default branch CI is green.
2. Update the package version, changelog, citation metadata, and documentation.
3. Confirm `python -m build` and `python -m twine check dist/*` succeed.
4. Create and push the matching version tag, for example:

   ```bash
   git checkout main
   git pull --ff-only
   git tag -a v0.5.0 -m "Agent Eval Kit v0.5.0"
   git push origin v0.5.0
   ```

5. The `Release` workflow will:
   - confirm the tagged commit is reachable from `main`,
   - verify that the tag matches `pyproject.toml`,
   - build the source distribution and wheel,
   - run Twine metadata checks,
   - attach both distributions to a GitHub Release,
   - publish the same distributions to PyPI through OIDC.

## Failure behavior

The GitHub Release and PyPI publishing jobs both depend on the same verified build artifact.

If PyPI Trusted Publishing has not been configured correctly, the PyPI job will fail without requiring or exposing a stored API token. Correct the Trusted Publisher configuration before retrying the failed job.

If the tag does not match the package version, or the tag points outside `main`, the workflow stops before publication.

## Security

Only the PyPI publishing job receives `id-token: write`. Build steps do not receive an OIDC publishing token.

Changes to `.github/workflows/release.yml` should be reviewed as security-sensitive changes because PyPI trusts the workflow identity.
