FROM node:20-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json* ./
RUN npm install

# Copy rest of files
COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
