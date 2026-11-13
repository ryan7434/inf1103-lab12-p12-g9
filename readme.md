## Running, testing and releasing

### Requirements
- Docker (for the tests and the container version), or Python 3.11 for running without Docker.
- A Gemini API key, passed as the `GEMINI_API_KEY` environment variable. Never commit the key.
- The application uses only Python's standard library. There is nothing to `pip install`.

### Run the automated tests
All tests run offline: the AI is replaced by a stub provider, so no API key or internet is needed.

```bash
# without Docker
python -m unittest discover -p "test_*.py" -v

# inside Docker, with the network switched off to prove no live API is used
docker build -t inf1103-p12-g9 .
docker run --rm --network none inf1103-p12-g9 python -m unittest discover -p "test_*.py" -v
```

### Run the application
```bash
# Docker (interactive: -it is needed because the app reads user input)
docker run -it --rm -e GEMINI_API_KEY=<your key> inf1103-p12-g9 python FoodAI.py

# without Docker
python FoodAI.py
```
PowerShell: set the key first with `$env:GEMINI_API_KEY="<your key>"`, then use `-e GEMINI_API_KEY=$env:GEMINI_API_KEY`.

Saved recipes are written to `recipes_history.json` inside the container and are lost when the
container is removed. To keep them on your computer, create the file first and mount it
(PowerShell):

```powershell
if (-not (Test-Path recipes_history.json)) { Set-Content recipes_history.json "[]" }
docker run -it --rm -e GEMINI_API_KEY=$env:GEMINI_API_KEY `
  -v "${PWD}/recipes_history.json:/usr/src/app/recipes_history.json" `
  inf1103-p12-g9 python FoodAI.py
```
The file must exist before the first run, otherwise Docker creates a folder with that name.
The container's working folder is `/usr/src/app` (the `WORKDIR` in the Dockerfile).

### Continuous integration (CI)
`.github/workflows/tests.yml` runs on every push to any branch, on every pull request into `main`, and on version tags.
The `test` job:
1. runs all `test_*.py` files with `unittest`,
2. builds the Docker image,
3. runs the same tests inside the image with `--network none`.

A change is only safe to merge when this job is green.

### Continuous deployment (CD): automated Docker release
The `publish` job in the same workflow is triggered by a **version tag** such as `v1.0.0`.
It has `needs: test`, so it starts only if every test passed. If a test or the build fails,
nothing is published.

What the `publish` job does:
1. checks that the tag looks like `vMAJOR.MINOR.PATCH`,
2. builds the FoodAI image,
3. runs the tests inside that image with `--network none`,
4. checks that no `GEMINI_API_KEY` is baked into the image,
5. pushes `ghcr.io/ryan7434/inf1103-p12-g9:<version>` and `:latest` to the GitHub Container Registry.

API keys are never part of the image. Each user passes their own key when running it.

#### Making a release
```bash
git tag -a v1.0.0 -m "First release"
git push origin v1.0.0
```
Then open the repository's **Actions** tab, wait for the green run, and check
**Packages** on the repository page for the new version.
The package must be set to public (Package settings) so others can pull it without logging in.

#### Running a released version
```bash
docker run -it --rm --pull always -e GEMINI_API_KEY=<your key> \
  ghcr.io/ryan7434/inf1103-p12-g9:1.0.0 python FoodAI.py
```
Use `:latest` for the newest release.