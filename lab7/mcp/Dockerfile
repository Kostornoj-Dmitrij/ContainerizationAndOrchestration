FROM node:20-alpine

RUN npm install -g mcp-proxy \
    @modelcontextprotocol/server-filesystem \
    @modelcontextprotocol/server-memory

EXPOSE 8081

CMD ["mcp-proxy", "--host", "0.0.0.0", "--port", "8081", "--", "mcp-server-filesystem", "/data"]