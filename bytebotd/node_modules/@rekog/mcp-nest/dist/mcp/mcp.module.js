"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var McpModule_1;
Object.defineProperty(exports, "__esModule", { value: true });
exports.McpModule = void 0;
const common_1 = require("@nestjs/common");
const core_1 = require("@nestjs/core");
const interfaces_1 = require("./interfaces");
const mcp_executor_service_1 = require("./services/mcp-executor.service");
const mcp_registry_service_1 = require("./services/mcp-registry.service");
const mcp_sse_service_1 = require("./services/mcp-sse.service");
const mcp_streamable_http_service_1 = require("./services/mcp-streamable-http.service");
const sse_ping_service_1 = require("./services/sse-ping.service");
const sse_controller_factory_1 = require("./transport/sse.controller.factory");
const stdio_service_1 = require("./transport/stdio.service");
const streamable_http_controller_factory_1 = require("./transport/streamable-http.controller.factory");
const normalize_endpoint_1 = require("./utils/normalize-endpoint");
let instanceIdCounter = 0;
let McpModule = McpModule_1 = class McpModule {
    constructor() {
        this.__isMcpModule = true;
    }
    static forRoot(options) {
        const defaultOptions = {
            transport: [
                interfaces_1.McpTransportType.SSE,
                interfaces_1.McpTransportType.STREAMABLE_HTTP,
                interfaces_1.McpTransportType.STDIO,
            ],
            sseEndpoint: 'sse',
            messagesEndpoint: 'messages',
            mcpEndpoint: 'mcp',
            guards: [],
            decorators: [],
            streamableHttp: {
                enableJsonResponse: true,
                sessionIdGenerator: undefined,
                statelessMode: true,
            },
            sse: {
                pingEnabled: true,
                pingIntervalMs: 30000,
            },
        };
        const mergedOptions = { ...defaultOptions, ...options };
        mergedOptions.sseEndpoint = (0, normalize_endpoint_1.normalizeEndpoint)(mergedOptions.sseEndpoint);
        mergedOptions.messagesEndpoint = (0, normalize_endpoint_1.normalizeEndpoint)(mergedOptions.messagesEndpoint);
        mergedOptions.mcpEndpoint = (0, normalize_endpoint_1.normalizeEndpoint)(mergedOptions.mcpEndpoint);
        const moduleId = `mcp-module-${instanceIdCounter++}`;
        const providers = this.createProvidersFromOptions(mergedOptions, moduleId);
        const controllers = this.createControllersFromOptions(mergedOptions);
        return {
            module: McpModule_1,
            controllers,
            providers,
            exports: [mcp_registry_service_1.McpRegistryService, mcp_sse_service_1.McpSseService, mcp_streamable_http_service_1.McpStreamableHttpService],
        };
    }
    static forRootAsync(options) {
        const moduleId = `mcp-module-${instanceIdCounter++}`;
        const asyncProviders = this.createAsyncProviders(options);
        const baseProviders = [
            {
                provide: 'MCP_MODULE_ID',
                useValue: moduleId,
            },
            mcp_registry_service_1.McpRegistryService,
            mcp_executor_service_1.McpExecutorService,
            sse_ping_service_1.SsePingService,
            mcp_sse_service_1.McpSseService,
            mcp_streamable_http_service_1.McpStreamableHttpService,
            stdio_service_1.StdioService,
        ];
        return {
            module: McpModule_1,
            imports: options.imports ?? [],
            controllers: [],
            providers: [
                ...asyncProviders,
                ...baseProviders,
                ...(options.extraProviders ?? []),
            ],
            exports: [mcp_registry_service_1.McpRegistryService, mcp_sse_service_1.McpSseService, mcp_streamable_http_service_1.McpStreamableHttpService],
        };
    }
    static createAsyncProviders(options) {
        if (options.useFactory) {
            return [
                {
                    provide: 'MCP_OPTIONS',
                    useFactory: async (...args) => {
                        const resolved = await options.useFactory(...args);
                        return this.mergeAndNormalizeAsyncOptions(resolved);
                    },
                    inject: options.inject ?? [],
                },
            ];
        }
        const inject = [];
        let optionsFactoryProvider;
        if (options.useExisting || options.useClass) {
            const useExisting = options.useExisting || options.useClass;
            inject.push(useExisting);
            if (options.useClass) {
                optionsFactoryProvider = {
                    provide: options.useClass,
                    useClass: options.useClass,
                };
            }
            return [
                ...(optionsFactoryProvider ? [optionsFactoryProvider] : []),
                {
                    provide: 'MCP_OPTIONS',
                    useFactory: async (factory) => {
                        const resolved = await factory.createMcpOptions();
                        return this.mergeAndNormalizeAsyncOptions(resolved);
                    },
                    inject,
                },
            ];
        }
        throw new Error('Invalid McpModuleAsyncOptions configuration.');
    }
    static mergeAndNormalizeAsyncOptions(resolved) {
        const defaultOptions = {
            sseEndpoint: 'sse',
            messagesEndpoint: 'messages',
            mcpEndpoint: 'mcp',
            guards: [],
            decorators: [],
            streamableHttp: {
                enableJsonResponse: true,
                sessionIdGenerator: undefined,
                statelessMode: true,
            },
            sse: {
                pingEnabled: true,
                pingIntervalMs: 30000,
            },
        };
        const merged = { ...defaultOptions, ...resolved };
        merged.sseEndpoint = (0, normalize_endpoint_1.normalizeEndpoint)(merged.sseEndpoint);
        merged.messagesEndpoint = (0, normalize_endpoint_1.normalizeEndpoint)(merged.messagesEndpoint);
        merged.mcpEndpoint = (0, normalize_endpoint_1.normalizeEndpoint)(merged.mcpEndpoint);
        return merged;
    }
    static createControllersFromOptions(options) {
        const sseEndpoint = options.sseEndpoint ?? 'sse';
        const messagesEndpoint = options.messagesEndpoint ?? 'messages';
        const mcpEndpoint = options.mcpEndpoint ?? 'mcp';
        const guards = options.guards ?? [];
        const transports = Array.isArray(options.transport)
            ? options.transport
            : [options.transport ?? interfaces_1.McpTransportType.SSE];
        const controllers = [];
        const decorators = options.decorators ?? [];
        const apiPrefix = options.apiPrefix ?? '';
        if (transports.includes(interfaces_1.McpTransportType.SSE)) {
            const sseController = (0, sse_controller_factory_1.createSseController)(sseEndpoint, messagesEndpoint, apiPrefix, guards, decorators);
            controllers.push(sseController);
        }
        if (transports.includes(interfaces_1.McpTransportType.STREAMABLE_HTTP)) {
            const streamableHttpController = (0, streamable_http_controller_factory_1.createStreamableHttpController)(mcpEndpoint, apiPrefix, guards, decorators);
            controllers.push(streamableHttpController);
        }
        if (transports.includes(interfaces_1.McpTransportType.STDIO)) {
        }
        return controllers;
    }
    static createProvidersFromOptions(options, moduleId) {
        const providers = [
            {
                provide: 'MCP_OPTIONS',
                useValue: options,
            },
            {
                provide: 'MCP_MODULE_ID',
                useValue: moduleId,
            },
            mcp_registry_service_1.McpRegistryService,
            mcp_executor_service_1.McpExecutorService,
            sse_ping_service_1.SsePingService,
            mcp_sse_service_1.McpSseService,
            mcp_streamable_http_service_1.McpStreamableHttpService,
            stdio_service_1.StdioService,
        ];
        return providers;
    }
};
exports.McpModule = McpModule;
exports.McpModule = McpModule = McpModule_1 = __decorate([
    (0, common_1.Module)({
        imports: [core_1.DiscoveryModule],
        providers: [mcp_registry_service_1.McpRegistryService, mcp_executor_service_1.McpExecutorService],
    })
], McpModule);
//# sourceMappingURL=mcp.module.js.map