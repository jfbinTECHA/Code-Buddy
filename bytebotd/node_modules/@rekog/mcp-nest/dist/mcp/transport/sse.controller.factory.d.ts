import { CanActivate, Logger, Type } from '@nestjs/common';
import { McpOptions } from '../interfaces';
import { McpSseService } from '../services/mcp-sse.service';
export declare function createSseController(sseEndpoint: string, messagesEndpoint: string, apiPrefix: string, guards?: Type<CanActivate>[], decorators?: ClassDecorator[]): {
    new (options: McpOptions, mcpSseService: McpSseService): {
        readonly logger: Logger;
        readonly options: McpOptions;
        readonly mcpSseService: McpSseService;
        onModuleInit(): void;
        sse(rawReq: any, rawRes: any): Promise<void>;
        messages(rawReq: any, rawRes: any, body: unknown): Promise<void>;
    };
};
//# sourceMappingURL=sse.controller.factory.d.ts.map