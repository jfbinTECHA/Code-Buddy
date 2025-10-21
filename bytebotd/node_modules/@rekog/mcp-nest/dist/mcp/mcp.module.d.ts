import { DynamicModule } from '@nestjs/common';
import type { McpOptions, McpModuleAsyncOptions } from './interfaces';
export declare class McpModule {
    readonly __isMcpModule = true;
    static forRoot(options: McpOptions): DynamicModule;
    static forRootAsync(options: McpModuleAsyncOptions): DynamicModule;
    private static createAsyncProviders;
    private static mergeAndNormalizeAsyncOptions;
    private static createControllersFromOptions;
    private static createProvidersFromOptions;
}
//# sourceMappingURL=mcp.module.d.ts.map