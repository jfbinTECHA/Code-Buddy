"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const testing_1 = require("@nestjs/testing");
const jwt = __importStar(require("jsonwebtoken"));
const jwt_token_service_1 = require("./jwt-token.service");
describe('JwtTokenService', () => {
    const baseOptions = {
        jwtSecret: 'a'.repeat(32),
        jwtIssuer: 'http://localhost',
        serverUrl: 'http://localhost',
        jwtAccessTokenExpiresIn: '2h',
        jwtRefreshTokenExpiresIn: '3d',
        enableRefreshTokens: true,
    };
    let service;
    beforeEach(async () => {
        const module = await testing_1.Test.createTestingModule({
            providers: [
                jwt_token_service_1.JwtTokenService,
                {
                    provide: 'OAUTH_MODULE_OPTIONS',
                    useValue: baseOptions,
                },
            ],
        }).compile();
        service = module.get(jwt_token_service_1.JwtTokenService);
    });
    it('generates tokens with configured expirations', () => {
        const tokens = service.generateTokenPair('user1', 'client1', '', 'resource1');
        expect(tokens.refresh_token).toBeDefined();
        const decoded = jwt.decode(tokens.access_token);
        const decodedRefresh = jwt.decode(tokens.refresh_token);
        expect(decoded.exp - decoded.iat).toBe(2 * 60 * 60);
        expect(decodedRefresh.exp - decodedRefresh.iat).toBe(3 * 24 * 60 * 60);
        expect(tokens.expires_in).toBe(2 * 60 * 60);
    });
    it('can disable refresh tokens', async () => {
        const module = await testing_1.Test.createTestingModule({
            providers: [
                jwt_token_service_1.JwtTokenService,
                {
                    provide: 'OAUTH_MODULE_OPTIONS',
                    useValue: { ...baseOptions, enableRefreshTokens: false },
                },
            ],
        }).compile();
        const serviceNoRefresh = module.get(jwt_token_service_1.JwtTokenService);
        const tokens = serviceNoRefresh.generateTokenPair('user1', 'client1', '', 'resource1');
        expect(tokens.refresh_token).toBeUndefined();
        expect(tokens.expires_in).toBe(2 * 60 * 60);
    });
});
//# sourceMappingURL=jwt-token.service.spec.js.map