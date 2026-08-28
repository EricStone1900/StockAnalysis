import { z } from 'zod';

const serviceConfigSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  SERVICE_NAME: z.string().min(1),
});

export type ServiceConfig = z.infer<typeof serviceConfigSchema>;

export function readServiceConfig(environment: NodeJS.ProcessEnv): ServiceConfig {
  return serviceConfigSchema.parse(environment);
}
