FROM node:14 AS build
WORKDIR /app

RUN rm -rf node_modules package-lock.json

COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]