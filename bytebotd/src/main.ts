import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { createProxyMiddleware } from 'http-proxy-middleware';
import * as express from 'express';
import { json, urlencoded } from 'express';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Configure body parser with increased payload size limit (50MB)
  app.use(json({ limit: '50mb' }));
  app.use(urlencoded({ limit: '50mb', extended: true }));

  // Enable CORS
  app.enableCors({
    origin: '*',
    methods: ['GET', 'POST'],
    credentials: true,
  });

  // Expose /health at root level for external monitoring
  app.use('/health', (req, res) => res.json({ status: 'ok' }));

  const wsProxy = createProxyMiddleware({
    target: 'http://localhost:6080',
    ws: true,
    changeOrigin: true,
    pathRewrite: { '^/websockify': '/' },
  });
  app.use('/websockify', express.raw({ type: '*/*' }), wsProxy);
  const server = await app.listen(process.env.PORT || 9990, '0.0.0.0');

  // Selective upgrade routing
  server.on('upgrade', (req, socket, head) => {
    if (req.url?.startsWith('/websockify')) {
      wsProxy.upgrade(req, socket, head);
    }
    // else let Socket.IO/Nest handle it by not hijacking the socket
  });
}
bootstrap();
