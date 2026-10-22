FROM golang:1.27-bookworm AS go
FROM node:24-bookworm AS node
FROM ghcr.io/actions/actions-runner:2.338.1

USER root
COPY --from=go /usr/local/go /usr/local/go
COPY --from=node /usr/local/bin/node /usr/local/bin/node
ENV PATH="/usr/local/go/bin:/opt/vite-plus/bin:${PATH}" \
    VP_HOME=/opt/vite-plus \
    GOMODCACHE=/cache/go-mod \
    GOCACHE=/cache/go-build \
    npm_config_store_dir=/cache/pnpm
RUN curl -fsSL https://vite.plus -o /tmp/install-vp.sh \
    && VP_NODE_MANAGER=no VP_PM_MANAGER=yes bash /tmp/install-vp.sh \
    && rm /tmp/install-vp.sh \
    && chmod -R a+rX /opt/vite-plus
USER runner
