FROM debian:bookworm-slim

ARG USER_ID=1000
ARG GROUP_ID=1000

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        ffmpeg \
        git \
        python3 \
        python3-venv \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${GROUP_ID}" worker \
    && useradd --uid "${USER_ID}" --gid "${GROUP_ID}" --create-home --shell /bin/bash worker

ENV PATH="/home/worker/.local/bin:${PATH}"

WORKDIR /workspace
USER worker

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash"]
