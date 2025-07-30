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

# Switch to the root user to perform user management tasks
USER root

# Create a restricted user (appuser) and group (appgroup) for running the application
RUN addgroup -S appgroup && adduser -S -h /etc/appuser appuser -G appgroup

# Ensure that the appuser owns the application files and directories
RUN chown -R appuser:appgroup ${PROJECT_DIR} /usr/local/lib/python3.12/site-packages /usr/local/bin ${PROMETHEUS_MULTIPROC_DIR}

# Switch to the restricted user to enhance security
USER appuser

# Start the inspector
CMD ["npm", "start"]
