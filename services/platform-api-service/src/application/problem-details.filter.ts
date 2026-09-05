import { Catch, type ArgumentsHost, type ExceptionFilter, HttpException } from '@nestjs/common';
import { toProblemDetails } from './security.js';

@Catch()
export class ProblemDetailsFilter implements ExceptionFilter {
  public catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<{ status: (code: number) => { send: (body: unknown) => void } }>();
    const request = host.switchToHttp().getRequest<{ headers?: Record<string, string | undefined> }>();
    const requestId = request.headers?.['x-request-id'] ?? 'unknown-request';
    const status = exception instanceof HttpException ? exception.getStatus() : 500;
    response.status(status).send(toProblemDetails(exception, requestId, status));
  }
}
