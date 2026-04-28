FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY tsconfig.json ./
COPY src/ ./src/

RUN npm run build

FROM node:20-alpine

RUN apk add --no-cache ffmpeg python3 py3-pip
RUN pip3 install --break-system-packages edge-tts yt-dlp

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY --from=builder /app/dist/ ./dist/
COPY assets/ ./assets/

RUN mkdir -p downloads temp logs

ENV NODE_ENV=production

CMD ["node", "dist/index.js"]
