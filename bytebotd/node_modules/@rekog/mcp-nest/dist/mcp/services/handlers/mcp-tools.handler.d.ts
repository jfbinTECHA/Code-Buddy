import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { ModuleRef } from '@nestjs/core';
import { McpRegistryService } from '../mcp-registry.service';
import { McpHandlerBase } from './mcp-handler.base';
import { HttpRequest } from '../../interfaces/http-adapter.interface';
export declare class McpToolsHandler extends McpHandlerBase {
    private readonly mcpModuleId;
    constructor(moduleRef: ModuleRef, registry: McpRegistryService, mcpModuleId: string);
    private buildDefaultContentBlock;
    private formatToolResult;
    registerHandlers(mcpServer: McpServer, httpRequest: HttpRequest): void;
}
//# sourceMappingURL=mcp-tools.handler.d.ts.map