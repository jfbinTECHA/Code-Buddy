import { CanActivate, ExecutionContext } from '@nestjs/common';
import { Request } from 'express';
import { JwtPayload, JwtTokenService } from '../services/jwt-token.service';
import { IOAuthStore } from '../stores/oauth-store.interface';
export interface AuthenticatedRequest extends Request {
    user: JwtPayload;
}
export declare class McpAuthJwtGuard implements CanActivate {
    private readonly jwtTokenService;
    private readonly store;
    constructor(jwtTokenService: JwtTokenService, store: IOAuthStore);
    canActivate(context: ExecutionContext): Promise<boolean>;
    private extractTokenFromHeader;
}
//# sourceMappingURL=jwt-auth.guard.d.ts.map