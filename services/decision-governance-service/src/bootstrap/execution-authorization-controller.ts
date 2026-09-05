import { BadRequestException, Controller, Headers, Injectable, Post, Body, ServiceUnavailableException, UnauthorizedException, Inject } from '@nestjs/common';
import type { ExecutionAuthorizationGrant } from '@stock/contracts';
import { GovernanceService } from '../application/governance-service.js';
import type { ExecutionAuthorizationInput } from '../application/execution-authorization-service.js';
import type { ResourceReservationReader } from '../application/resource-reservation-reader.js';

@Injectable()
export class InternalServiceTokenGuard {
  canActivate(headers: Record<string, string | undefined>): void {
    const expected = process.env.GOVERNANCE_INTERNAL_TOKEN;
    if (!expected || headers['x-service-token'] !== expected) throw new UnauthorizedException('invalid governance service identity');
  }
}

@Controller('/internal/v1/execution-authorizations')
export class ExecutionAuthorizationController {
  constructor(private readonly service: GovernanceService, @Inject('ResourceReservationReader') private readonly resources: ResourceReservationReader, private readonly guard = new InternalServiceTokenGuard()) {}
  @Post()
  async issue(@Headers() headers: Record<string, string | undefined>, @Body() body: ExecutionAuthorizationInput): Promise<ExecutionAuthorizationGrant> {
    this.guard.canActivate(headers);
    try {
      const resource = await this.resources.get(body.resourceReservationId);
      return await this.service.issueExecutionAuthorization(body, resource as never);
    } catch (error) {
      if (error instanceof Error && error.message.includes('not configured')) throw new ServiceUnavailableException(error.message);
      throw new BadRequestException(error instanceof Error ? error.message : 'invalid execution authorization');
    }
  }
}
