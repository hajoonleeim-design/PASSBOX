# PASSBOX 프런트엔드: Vite로 빌드한 정적 파일을 nginx가 서빙하고 /api 는 백엔드로 넘긴다.
# 같은 주소에서 화면과 API가 함께 나가므로 브라우저 CORS 설정이 필요 없다.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_TENANT_ID=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_TENANT_ID=$VITE_TENANT_ID
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
