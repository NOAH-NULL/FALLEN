# Production load-test plan

1. Gateway event replay: synthetic guild/message/member event streams at expected peak rates.
2. DB saturation: measure p95/p99 query latency, pool wait time, transaction duration, deadlocks.
3. Redis: measure cache hit ratio, command latency, lock contention and Pub/Sub lag.
4. Reconnect storm: restart shard workers while maintaining traffic.
5. Worker backpressure: flood welcome/render and reminder queues and verify bounded memory.
6. API rate limits: verify Discord 429 handling and retry behavior.
7. Voice: benchmark external Lavalink nodes separately from gateway workers.
8. Chaos: terminate one shard, one bot worker, Redis primary, and DB connection pool members.

Capacity claims must come from measured results, not from the number of Kubernetes replicas.
