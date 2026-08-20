---
name: full-performance-audit
description: Audit application performance including latency, throughput, memory, and bundle size. Use when profiling applications, identifying bottlenecks, or optimizing performance.
when-to-use: "Use on demand for measured regressions in bundle, query, memory, latency, or Core Web Vitals (LCP, INP, CLS)."

---

# Full Performance Audit

## When to Use

- Profiling application performance
- Identifying bottlenecks
- Optimizing slow endpoints
- Reducing bundle size
- Improving Core Web Vitals

## Input

- Application metrics
- User complaints
- Performance goals

## Output

- Performance report
- Bottleneck analysis
- Optimization recommendations
- Implementation plan

## Checklist

1. **Frontend Audit**
   - Measure Core Web Vitals (LCP, INP, CLS; FID is legacy)
   - Analyze bundle size
   - Check render performance
   - Optimize images/assets

2. **Backend Audit**
   - Profile API endpoints
   - Identify N+1 queries
   - Check database indexes
   - Monitor memory usage

3. **Infrastructure Audit**
   - Check server resources
   - Analyze network latency
   - Review caching strategy
   - Monitor error rates

4. **Optimization**
   - Implement code splitting
   - Add database indexes
   - Optimize queries
   - Configure caching

## Best Practices

- Measure before optimizing
- Use profiling tools
- Set performance budgets
- Monitor continuously
- Focus on bottlenecks
- Test under load

## Anti-Patterns

❌ Optimizing without measuring
❌ Premature optimization
❌ Ignoring database queries
❌ Not monitoring in production
❌ One-time optimization

## Validation

- Performance meets targets
- No regressions introduced
- Monitoring in place
- Alerts configured

## Examples

### Example 1: Performance Profiling
```typescript
// lib/profiler.ts
import { performance } from 'perf_hooks';

export function profile<T>(name: string, fn: () => Promise<T>): Promise<T> {
  return async () => {
    const start = performance.now();
    
    try {
      const result = await fn();
      const duration = performance.now() - start;
      
      console.log(JSON.stringify({
        type: 'performance',
        name,
        duration,
        status: 'success',
      }));
      
      return result;
    } catch (error) {
      const duration = performance.now() - start;
      
      console.log(JSON.stringify({
        type: 'performance',
        name,
        duration,
        status: 'error',
      }));
      
      throw error;
    }
  };
}

// Usage
const users = await profile('fetchUsers', () => db.user.findMany());
```

### Example 2: N+1 Query Detection
```typescript
// lib/queryMonitor.ts
let queryCount = 0;

export function monitorQueries() {
  prisma.$on('query', (e) => {
    queryCount++;
    console.log(JSON.stringify({
      type: 'query',
      query: e.query,
      duration: e.duration,
      count: queryCount,
    }));
  });
}

export function resetQueryCount() {
  queryCount = 0;
}

export function getQueryCount() {
  return queryCount;
}
```

### Example 3: Bundle Analysis
```javascript
// webpack.config.js
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  plugins: [
    new BundleAnalyzerPlugin({
      analyzerMode: 'static',
      reportFilename: 'bundle-report.html',
    }),
  ],
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
      },
    },
  },
};
```

### Example 4: Load Testing
```typescript
// tests/load.ts
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://localhost:3000/api/users');
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
```

## Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| LCP | < 2.5s | > 4s |
| INP | < 200ms | > 500ms |
| CLS | < 0.1 | > 0.25 |
| TTFB | < 200ms | > 600ms |
| API Response | < 200ms | > 1s |
| Bundle Size | < 200KB | > 500KB |

## Output Structure

```
├── reports/
│   ├── performance-report.md
│   ├── bundle-report.html
│   └── load-test-results.json
├── tools/
│   ├── profiler.ts
│   ├── queryMonitor.ts
│   └── lighthouse.config.js
└── tests/
    └── load.ts
```
