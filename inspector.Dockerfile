# Inspector Dockerfile
FROM node:20-alpine

# Install git
RUN apk add --no-cache git

# Clone the MCP Inspector repository
RUN git clone https://github.com/modelcontextprotocol/inspector.git /app
WORKDIR /app

# Install dependencies and build
RUN npm install && npm run build

# Set environment variables if needed
ENV DANGEROUSLY_OMIT_AUTH=true

# Expose the default port
EXPOSE 6277

# Start the inspector
CMD ["npm", "start"]
