# AI Agent Project

Two-agent example: a Senior Research Analyst (search + verify) and a Technical Content Writer (synthesizes verified facts into Markdown).

Tavily integration
- The project includes `tavily_adapter.TavilyClient` which will be used when running with `--no-mock`.
- Configure the client with `TAVILY_API_KEY` (required) and optionally `TAVILY_API_BASE`.

Run (mock):

    python run_team.py --topic "Quantum Computing"

Run (real Tavily):

    export TAVILY_API_KEY=your_real_key
    python run_team.py --topic "Quantum Computing" --no-mock

[![CI](https://github.com/mohtashimnawaz/ai-agent-project/actions/workflows/ci.yml/badge.svg)](https://github.com/mohtashimnawaz/ai-agent-project/actions/workflows/ci.yml)

See `USAGE.md` for more details.

---

## CI / GitHub Actions onboarding ⚙️

- Ensure Actions are enabled: **Repository → Settings → Actions → General → Allow all actions** (or follow organization policy). ✅
- Add required repository secrets if you want integration runs: **TAVILY_API_KEY**, **TAVILY_REDIS_CACHE_URL**, and (if publishing) **DOCKER_USERNAME**, **DOCKER_PASSWORD**, **DOCKER_REGISTRY**. 🔐
- You can run CI manually in the Actions UI: **Actions → CI → Run workflow → select branch → Run workflow**.
- Integration tests are guarded with `@pytest.mark.integration` and will only run when `TAVILY_API_KEY` and `TAVILY_REDIS_CACHE_URL` are set; to run locally: set env vars and run `./scripts/run_integration_tests.sh`.
- Troubleshooting tips: check workflow logs (expand the failing step), ensure Secrets are set, and verify repository Actions permissions. 🛠️
