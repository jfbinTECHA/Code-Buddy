import { InjectionToken, OnApplicationBootstrap } from '@nestjs/common';
import { DiscoveryService, MetadataScanner, ModulesContainer } from '@nestjs/core';
import { ToolMetadata } from '../decorators';
import { ResourceMetadata } from '../decorators/resource.decorator';
import { PromptMetadata } from '../decorators/prompt.decorator';
import { ResourceTemplateMetadata } from '../decorators/resource-template.decorator';
export type DiscoveredTool<T extends object> = {
    type: 'tool' | 'resource' | 'resource-template' | 'prompt';
    metadata: T;
    providerClass: InjectionToken;
    methodName: string;
};
export type InjectionTokenWithName = InjectionToken & {
    name: string;
};
export declare class McpRegistryService implements OnApplicationBootstrap {
    private readonly discovery;
    private readonly metadataScanner;
    private readonly modulesContainer;
    private readonly logger;
    private discoveredToolsByMcpModuleId;
    constructor(discovery: DiscoveryService, metadataScanner: MetadataScanner, modulesContainer: ModulesContainer);
    onApplicationBootstrap(): void;
    private discoverTools;
    private collectSubtreeModules;
    private discoverToolsForModuleSubtree;
    private addDiscovery;
    private addDiscoveryPrompt;
    private addDiscoveryTool;
    private addDiscoveryResource;
    private addDiscoveryResourceTemplate;
    getMcpModuleIds(): string[];
    getTools(mcpModuleId: string): DiscoveredTool<ToolMetadata>[];
    findTool(mcpModuleId: string, name: string): DiscoveredTool<ToolMetadata> | undefined;
    getResources(mcpModuleId: string): DiscoveredTool<ResourceMetadata>[];
    findResource(mcpModuleId: string, name: string): DiscoveredTool<ResourceMetadata> | undefined;
    getResourceTemplates(mcpModuleId: string): DiscoveredTool<ResourceTemplateMetadata>[];
    findResourceTemplate(mcpModuleId: string, name: string): DiscoveredTool<ResourceTemplateMetadata> | undefined;
    getPrompts(mcpModuleId: string): DiscoveredTool<PromptMetadata>[];
    findPrompt(mcpModuleId: string, name: string): DiscoveredTool<PromptMetadata> | undefined;
    private convertTemplate;
    private convertUri;
    findResourceByUri(mcpModuleId: string, uri: string): {
        resource: DiscoveredTool<ResourceMetadata>;
        params: Record<string, string>;
    } | undefined;
    findResourceTemplateByUri(mcpModuleId: string, uri: string): {
        resourceTemplate: DiscoveredTool<ResourceTemplateMetadata>;
        params: Record<string, string>;
    } | undefined;
}
//# sourceMappingURL=mcp-registry.service.d.ts.map