FROM node:24-bookworm-slim

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=10000

WORKDIR /app

# Copy only the studio. Financial data, widgets, Git metadata, tests and secrets
# never enter this production image. Credentials are runtime environment values.
COPY editorial-studio.html ./editorial-studio.html
COPY assets/editorial-*.css ./assets/
COPY assets/editorial-*.js ./assets/
COPY assets/editorial-studio/ ./assets/editorial-studio/
COPY services/editorial-studio/server.mjs services/editorial-studio/auth.mjs ./services/editorial-studio/

# Source files can come from a workspace with a restrictive umask. Keep code
# root-owned and readable by the unprivileged runtime user.
RUN chmod -R go-w,a+rX /app

USER node
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:' + (process.env.PORT || 10000) + '/healthz').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

CMD ["node", "services/editorial-studio/server.mjs"]
