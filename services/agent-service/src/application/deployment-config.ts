export const AGENT_IDS = ['stock-analysis', 'financial-news', 'market-monitor', 'market-state', 'main-decision', 'risk-review'] as const;
export type AgentId = typeof AGENT_IDS[number];
export interface AgentDeploymentConfig { agentId: AgentId; modelProfile: string; promptVersion: string; taskQueue: string; durableConsumer: string; allowedTools: readonly string[]; }

export function readAgentDeployment(env: Record<string, string | undefined>): AgentDeploymentConfig {
  const candidate = env.AGENT_ID;
  if (!candidate || !AGENT_IDS.includes(candidate as AgentId)) throw new Error('AGENT_ID must select exactly one approved agent');
  const agentId = candidate as AgentId;
  const modelProfile = env.AGENT_MODEL_PROFILE ?? 'fake';
  const promptVersion = env.AGENT_PROMPT_VERSION ?? 'fake-prompt-v1';
  const taskQueue = env.AGENT_TASK_QUEUE ?? `agent-${agentId}`;
  const durableConsumer = env.AGENT_DURABLE_CONSUMER ?? `agent-${agentId}-v1`;
  if (!taskQueue.includes(agentId) || !durableConsumer.includes(agentId)) throw new Error('task queue and durable consumer must be isolated by AGENT_ID');
  return { agentId, modelProfile, promptVersion, taskQueue, durableConsumer, allowedTools: (env.AGENT_ALLOWED_TOOLS ?? '').split(',').map((value) => value.trim()).filter(Boolean) };
}
