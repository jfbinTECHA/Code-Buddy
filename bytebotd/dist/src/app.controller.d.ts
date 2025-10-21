import { AppService } from './app.service';
export declare class AppController {
    private readonly appService;
    constructor(appService: AppService);
    getHealth(): {
        status: string;
    };
    getMetrics(): {
        uptime: number;
        memory: NodeJS.MemoryUsage;
        timestamp: number;
    };
    recoverOps(body: any): {
        status: string;
        alert: any;
    };
    getOpsHealth(): {
        status: string;
        uptime: number;
        timestamp: number;
    };
    redirectToVnc(host: string): {
        url: string;
    };
}
