import { describe, expect, it } from 'vitest';
import { assertDemoWorkerMode } from '../../src/worker-mode.js';
describe('Worker模式', () => {
  it('默认、真实模式和生产环境拒绝Fake绑定', () => {
    for (const env of [{}, { WORKFLOW_RUNTIME_MODE: 'real' }, { WORKFLOW_RUNTIME_MODE: 'demo', NODE_ENV: 'production' }]) expect(() => assertDemoWorkerMode(env)).toThrow();
  });
  it('demo必须显式关闭执行', () => {
    expect(() => assertDemoWorkerMode({ WORKFLOW_RUNTIME_MODE: 'demo' })).toThrow();
    expect(() => assertDemoWorkerMode({ WORKFLOW_RUNTIME_MODE: 'demo', WORKFLOW_EXECUTION_ENABLED: 'false' })).not.toThrow();
  });
});
