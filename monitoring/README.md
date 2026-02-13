# Monitoring Configuration

This directory contains monitoring and observability configurations for the SCBE-AETHERMOORE Memory Governance System.

## Contents

- **grafana-dashboard.json**: Grafana dashboard configuration for visualizing system metrics

## Overview

The monitoring stack provides comprehensive observability into:
- Memory sync operations
- Knowledge graph statistics
- Provenance tracking
- API performance
- System health
- Integration status

## Setup

### Grafana Dashboard

1. **Import Dashboard**
   ```bash
   # Using Grafana UI
   1. Navigate to Grafana (http://localhost:3000)
   2. Go to Dashboards > Import
   3. Upload grafana-dashboard.json
   4. Select your Prometheus data source
   5. Click Import
   ```

2. **Using Grafana API**
   ```bash
   curl -X POST http://localhost:3000/api/dashboards/db \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -d @grafana-dashboard.json
   ```

### Prometheus Configuration

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'scbe-aethermoore'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Metrics Reference

### Memory Governance Metrics
- `memory_sync_operations_total`: Total number of memory sync operations
- `memory_sync_duration_seconds`: Time taken for sync operations
- `sync_conflicts_total`: Number of synchronization conflicts
- `memory_usage_bytes`: Current memory usage

### Knowledge Graph Metrics
- `knowledge_graph_nodes_total`: Total nodes in the knowledge graph
- `knowledge_graph_relationships_total`: Total relationships
- `knowledge_graph_query_duration_seconds`: Query execution time

### Provenance Metrics
- `provenance_entries_total`: Total provenance entries
- `provenance_tracking_duration_seconds`: Time to create provenance records

### API Metrics
- `api_request_duration_seconds`: HTTP request duration histogram
- `api_requests_total`: Total API requests
- `errors_total`: Total error count

### Integration Metrics
- `integration_status`: Status of external integrations (HuggingFace, Notion, etc.)
- `integration_sync_duration_seconds`: Time for integration syncs

## Dashboard Panels

### 1. Memory Sync Operations
- **Type**: Graph
- **Metric**: `rate(memory_sync_operations_total[5m])`
- **Description**: Real-time sync operation rate

### 2. Knowledge Graph Nodes
- **Type**: Stat
- **Metric**: `knowledge_graph_nodes_total`
- **Description**: Current node count in knowledge graph

### 3. Provenance Entries
- **Type**: Stat
- **Metric**: `provenance_entries_total`
- **Description**: Total provenance tracking entries

### 4. API Request Duration
- **Type**: Graph
- **Metrics**: 
  - 95th percentile
  - 50th percentile
- **Description**: API latency distribution

### 5. Memory Usage
- **Type**: Graph
- **Metric**: `memory_usage_bytes`
- **Description**: System memory consumption

### 6. Integration Status
- **Type**: Table
- **Metric**: `integration_status`
- **Description**: Status of all platform integrations

### 7. Error Rate
- **Type**: Graph
- **Metric**: `rate(errors_total[5m])`
- **Description**: Error occurrence rate

### 8. Sync Conflicts
- **Type**: Stat
- **Metric**: `sync_conflicts_total`
- **Description**: Total synchronization conflicts

### 9. System Health
- **Type**: Stat
- **Metric**: `up`
- **Description**: Overall system availability status

## Alerting

Recommended Prometheus alert rules:

```yaml
groups:
  - name: scbe-aethermoore
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: MemorySyncFailure
        expr: increase(memory_sync_operations_total{status="failed"}[5m]) > 5
        for: 2m
        annotations:
          summary: "Multiple memory sync failures"
          
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "API latency exceeding 1 second"
          
      - alert: IntegrationDown
        expr: integration_status == 0
        for: 2m
        annotations:
          summary: "External integration unavailable"
```

## Customization

### Adding Custom Panels

1. Edit `grafana-dashboard.json`
2. Add new panel configuration
3. Reimport dashboard

### Modifying Refresh Rate

Change the `refresh` field in the dashboard JSON:
```json
"refresh": "30s"  // Options: "5s", "10s", "30s", "1m", "5m"
```

## Troubleshooting

### Dashboard Not Showing Data
1. Verify Prometheus is scraping metrics: `http://localhost:9090/targets`
2. Check SCBE-AETHERMOORE metrics endpoint: `http://localhost:8000/metrics`
3. Verify data source configuration in Grafana

### Missing Metrics
1. Ensure all system components are running
2. Check logs for metric export errors
3. Verify Prometheus scrape configuration

## Best Practices

1. **Set up alerting**: Configure alerts for critical metrics
2. **Monitor regularly**: Review dashboards daily
3. **Adjust thresholds**: Tune alert thresholds based on your workload
4. **Data retention**: Configure appropriate Prometheus retention period
5. **Backup dashboards**: Export and version control dashboard configurations

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [SCBE-AETHERMOORE Deployment Guide](../DEPLOYMENT.md)

## Support

For monitoring-related issues:
- GitHub Issues: https://github.com/issdandavis/SCBE-AETHERMOORE/issues
- Label: `monitoring`
