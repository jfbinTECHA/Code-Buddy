import { Controller, Get, Post, Body, Redirect, Headers } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('health')
  getHealth() {
    return { status: 'ok' };
  }

  @Get('metrics')
  getMetrics() {
    return {
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      timestamp: Date.now(),
    };
  }

  @Post('ops/recover')
  recoverOps(@Body() body: any) {
    console.log('Auto-recovery triggered from Grafana:', body);
    // Trigger recovery logic here
    return { status: 'recovery initiated', alert: body.alert };
  }

  @Get('ops/health')
  getOpsHealth() {
    return { status: 'ok', uptime: process.uptime(), timestamp: Date.now() };
  }

  // When a client makes a GET request to /vnc,
  // this method will automatically redirect them to the noVNC URL.
  @Get('vnc')
  // Leave the decorator empty but keep the status code.
  @Redirect(undefined, 302)
  redirectToVnc(@Headers('host') host: string) {
    return {
      url: `/novnc/vnc.html?host=${host}&path=websockify&resize=scale`,
    };
  }
}
