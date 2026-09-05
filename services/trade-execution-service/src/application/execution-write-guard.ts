import { timingSafeEqual } from 'node:crypto';
import { type CanActivate, type ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';

/** 传输层服务身份校验；不能替代ExecutionAuthorization的业务授权。 */
@Injectable()
export class ExecutionWriteGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const expected = process.env.EXECUTION_SERVICE_TOKEN;
    const request = context.switchToHttp().getRequest<{ headers: { authorization?: string } }>();
    const supplied = request.headers.authorization;
    if (!expected || expected.length < 32 || typeof supplied !== 'string') throw new UnauthorizedException('execution service identity required');
    const left = Buffer.from(supplied);
    const right = Buffer.from(`Bearer ${expected}`);
    if (left.length !== right.length || !timingSafeEqual(left, right)) throw new UnauthorizedException('invalid execution service identity');
    return true;
  }
}
