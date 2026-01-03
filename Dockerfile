# Multi-stage Dockerfile for a compact production image
FROM python:3.12-slim AS build
WORKDIR /app

COPY pyproject.toml /app/
RUN python - <<'PY'
import tomllib,subprocess
p = tomllib.loads(open('pyproject.toml','rb').read())
deps = p.get('project',{}).get('dependencies',[])
subprocess.check_call(['python','-m','pip','install','--upgrade','pip'])
subprocess.check_call(['python','-m','pip','install','--no-cache-dir'] + deps)
PY

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . /app

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "run_team.py"]
CMD ["--topic", "AI Research"]
