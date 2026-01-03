FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -r <(python - <<'PY'
import tomllib, subprocess, sys
p = tomllib.loads(open('pyproject.toml','rb').read())
deps = p.get('project',{}).get('dependencies',[])
print('\n'.join(deps))
PY)

COPY . /app

ENTRYPOINT ["python", "run_team.py"]
CMD ["--topic", "AI Research"]
