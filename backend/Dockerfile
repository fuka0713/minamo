FROM node:22-bookworm-slim
# 文字認識（OCR）用の Tesseract と日本語のデータ
RUN apt-get update \
  && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-jpn ca-certificates \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev
ENV NODE_ENV=production PORT=4000
EXPOSE 4000
CMD ["node", "dist/index.js"]
