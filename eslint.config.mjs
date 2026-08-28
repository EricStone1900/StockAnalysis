import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default [
  { ignores: ['**/dist/**', '**/.venv/**', '**/node_modules/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
];
