import { ModuleRef } from '@nestjs/core';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { McpRegistryService } from '../mcp-registry.service';
import { McpHandlerBase } from './mcp-handler.base';
import { HttpRequest } from '../../interfaces/http-adapter.interface';
export declare class McpPromptsHandler extends McpHandlerBase {
    private readonly mcpModuleId;
    constructor(moduleRef: ModuleRef, registry: McpRegistryService, mcpModuleId: string);
    registerHandlers(mcpServer: McpServer, httpRequest: HttpRequest): void;
}
//# sourceMappingURL=mcp-prompts.handler.d.ts.map