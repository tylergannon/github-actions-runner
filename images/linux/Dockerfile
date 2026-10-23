FROM golang:1.27.3-bookworm AS go
FROM node:24-bookworm AS node
FROM ghcr.io/actions/actions-runner:2.338.1
ARG TARGETARCH

USER root
RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential pkg-config lsof gh unzip zsh \
    && rm -rf /var/lib/apt/lists/*
COPY --from=go /usr/local/go /usr/local/go
COPY --from=node /usr/local/bin/node /usr/local/bin/node
# Required by the existing Linux client-handoff checks. Install once in the
# image so the consuming workflow's version check can reuse it.
RUN if [ "$TARGETARCH" = "amd64" ]; then \
      curl -fsSL https://github.com/lightpanda-io/browser/releases/download/1.0.1/lightpanda-x86_64-linux -o /usr/local/bin/lightpanda \
      && echo '551747e35c51ba107b5d5277eca4b48e077b2a3b40f09a047bf6670448bc35fd  /usr/local/bin/lightpanda' | sha256sum -c - \
      && chmod +x /usr/local/bin/lightpanda; \
    fi
# Docker creates absent mount parents as root. The runner must own its work
# and HOME parents before permanent tool volumes are mounted below them.
RUN mkdir -p /home/runner/_work /home/runner/.local/share /home/runner/.cache \
    && chown -R runner:runner /home/runner/_work /home/runner/.local /home/runner/.cache
ENV PATH="/usr/local/go/bin:/opt/vite-plus/bin:${PATH}" \
    VP_HOME=/opt/vite-plus \
    GOMODCACHE=/cache/go-mod \
    GOCACHE=/cache/go-build \
    PNPM_CONFIG_STORE_DIR=/cache/pnpm/store \
    PNPM_CONFIG_CACHE_DIR=/cache/pnpm/metadata
RUN curl -fsSL https://vite.plus -o /tmp/install-vp.sh \
    && VP_NODE_MANAGER=no VP_PM_MANAGER=yes bash /tmp/install-vp.sh \
    && rm /tmp/install-vp.sh \
    && chown -R runner:runner /opt/vite-plus
USER runner
RUN vp env default pnpm@12 && vp env install pnpm@12
