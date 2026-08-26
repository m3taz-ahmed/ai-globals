FROM manimcommunity/manim:v0.19.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

USER root

# ffmpeg CLI is required by Code2Video's merge step; git is required to clone.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /manim

# Pin Code2Video upstream commit for reproducible builds
ARG CODE2VIDEO_REPO=https://github.com/showlab/Code2Video.git
ARG CODE2VIDEO_COMMIT=cf7fba33a6db9ff332ae2b8311a4aee1c58961c0

RUN git init /manim/code2video \
    && cd /manim/code2video \
    && git remote add origin ${CODE2VIDEO_REPO} \
    && git fetch --depth=1 origin ${CODE2VIDEO_COMMIT} \
    && git checkout FETCH_HEAD

WORKDIR /manim/code2video

# Install upstream Python dependencies (manim is already satisfied by base image)
RUN pip install --no-cache-dir -r src/requirements.txt

# Patch a small upstream bug: agent.py uses pathlib.Path without importing
# pathlib. The correct fix is to ensure the `Path` name is defined by adding
# the import at the top of the module (instead of leaving `Path` undefined).
RUN python -c "import pathlib; p = pathlib.Path('src/agent.py'); text = p.read_text(); lines = text.splitlines(); \
    if not any('from pathlib import Path' in l or 'import pathlib' in l for l in lines): \
        text = 'from pathlib import Path\n' + text; \
    p.write_text(text)"

# Copy container entrypoint
COPY --chown=manimuser:manimuser entrypoint.py /manim/code2video/entrypoint.py
RUN chmod +x /manim/code2video/entrypoint.py

# Output and working directories
RUN mkdir -p /manim/code2video/output /manim/code2video/src/CASES \
    && chown -R manimuser:manimuser /manim/code2video

VOLUME ["/manim/code2video/output"]

USER manimuser
WORKDIR /manim/code2video/src

ENTRYPOINT ["python", "/manim/code2video/entrypoint.py"]
