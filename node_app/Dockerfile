FROM node:20-alpine
WORKDIR /app
RUN mkdir -p /shared_logs
COPY package.json .
RUN npm install --omit=dev
COPY server.js .
CMD ["node", "server.js"]
