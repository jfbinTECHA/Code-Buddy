import { ApplicationConfig, ModuleRef } from '@nestjs/core';
import { McpOptions } from '../interfaces';
import { McpRegistryService } from './mcp-registry.service';
import { SsePingService } from './sse-ping.service';
export declare class McpSseService {
    private readonly options;
    private readonly mcpModuleId;
    private readonly applicationConfig;
    private readonly moduleRef;
    private readonly toolRegistry;
    private readonly pingService;
    private readonly logger;
    private readonly transports;
    private readonly mcpServers;
    constructor(options: McpOptions, mcpModuleId: string, applicationConfig: ApplicationConfig, moduleRef: ModuleRef, toolRegistry: McpRegistryService, pingService: SsePingService);
    initialize(): void;
    createSseConnection(rawReq: any, rawRes: any, messagesEndpoint: string, apiPrefix: string): Promise<void>;
    handleMessage(rawReq: any, rawRes: any, body: unknown): Promise<any>;
}
//# sourceMappingURL=mcp-sse.service.d.ts.map