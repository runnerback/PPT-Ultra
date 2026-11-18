// Return an explicitly configured enterprise registry, or the official npm registry.
// Do not probe mirrors, rewrite .npmrc, or silently fall back to another source.
const configured = process.env.PPT_ULTRA_NPM_REGISTRY || 'https://registry.npmjs.org';
let registry;
try { registry = new URL(configured); }
catch { throw new Error('PPT_ULTRA_NPM_REGISTRY must be a valid HTTPS registry URL'); }
if (registry.protocol !== 'https:' || registry.username || registry.password || registry.search || registry.hash) {
  throw new Error('PPT_ULTRA_NPM_REGISTRY must be an HTTPS registry URL without credentials, query or fragment');
}
process.stdout.write(registry.href.replace(/\/$/, '') + '\n');
