import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { ModuleRef } from '@nestjs/core';
import { McpRegistryService } from './mcp-registry.service';
import { HttpRequest } from '../interfaces/http-adapter.interface';
export declare class McpExecutorService {
    private logger;
    private toolsHandler;
    private resourcesHandler;
    private promptsHandler;
    constructor(moduleRef: ModuleRef, registry: McpRegistryService, mcpModuleId: string);
    registerRequestHandlers(mcpServer: McpServer, httpRequest: HttpRequest): void;
}
//# sourceMappingURL=mcp-executor.service.d.ts.map