-- =====================================================
-- ASOUD Platform - Development Database Initialization
-- =====================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create development schemas
CREATE SCHEMA IF NOT EXISTS dev_analytics;
CREATE SCHEMA IF NOT EXISTS dev_logs;
CREATE SCHEMA IF NOT EXISTS dev_cache;

-- Create development-specific tables for testing
CREATE TABLE IF NOT EXISTS dev_logs.request_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method VARCHAR(10),
    path TEXT,
    status_code INTEGER,
    response_time INTEGER,
    user_id UUID,
    ip_address INET
);

CREATE TABLE IF NOT EXISTS dev_analytics.performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    endpoint VARCHAR(255),
    avg_response_time DECIMAL(10,3),
    request_count INTEGER,
    error_count INTEGER
);

-- Create indexes for development tables
CREATE INDEX IF NOT EXISTS idx_request_logs_timestamp ON dev_logs.request_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_request_logs_user_id ON dev_logs.request_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_endpoint ON dev_analytics.performance_metrics(endpoint);

-- Development user and permissions
DO $$
BEGIN
    -- Create development role if not exists
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'asoud_dev_role') THEN
        CREATE ROLE asoud_dev_role WITH NOLOGIN;
    END IF;
    
    -- Grant permissions
    GRANT USAGE ON SCHEMA dev_analytics TO asoud_dev_role;
    GRANT USAGE ON SCHEMA dev_logs TO asoud_dev_role;
    GRANT USAGE ON SCHEMA dev_cache TO asoud_dev_role;
    
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dev_analytics TO asoud_dev_role;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dev_logs TO asoud_dev_role;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA dev_cache TO asoud_dev_role;
    
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dev_analytics TO asoud_dev_role;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dev_logs TO asoud_dev_role;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA dev_cache TO asoud_dev_role;
END
$$;

-- Development settings
ALTER DATABASE asoud_dev SET log_statement = 'all';
ALTER DATABASE asoud_dev SET log_duration = 'on';
ALTER DATABASE asoud_dev SET log_min_duration_statement = 100;

-- Insert development data
INSERT INTO dev_analytics.performance_metrics (endpoint, avg_response_time, request_count, error_count)
VALUES 
    ('/api/v1/health/', 50.123, 1000, 0),
    ('/api/v1/users/profile/', 120.456, 500, 2),
    ('/api/v1/products/list/', 200.789, 750, 5)
ON CONFLICT DO NOTHING;

-- Development views for monitoring
CREATE OR REPLACE VIEW dev_analytics.slow_queries AS
SELECT 
    endpoint,
    avg_response_time,
    request_count,
    error_count,
    (error_count * 100.0 / request_count) as error_rate
FROM dev_analytics.performance_metrics
WHERE avg_response_time > 100
ORDER BY avg_response_time DESC;

CREATE OR REPLACE VIEW dev_logs.recent_errors AS
SELECT 
    timestamp,
    method,
    path,
    status_code,
    response_time,
    ip_address
FROM dev_logs.request_logs
WHERE status_code >= 400
    AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Development functions
CREATE OR REPLACE FUNCTION dev_analytics.log_performance(
    p_endpoint VARCHAR(255),
    p_response_time DECIMAL(10,3)
) RETURNS VOID AS $$
BEGIN
    INSERT INTO dev_analytics.performance_metrics (endpoint, avg_response_time, request_count, error_count)
    VALUES (p_endpoint, p_response_time, 1, 0)
    ON CONFLICT (endpoint) DO UPDATE SET
        avg_response_time = (performance_metrics.avg_response_time * performance_metrics.request_count + p_response_time) / (performance_metrics.request_count + 1),
        request_count = performance_metrics.request_count + 1;
END;
$$ LANGUAGE plpgsql;

-- Cleanup function for development
CREATE OR REPLACE FUNCTION dev_logs.cleanup_old_logs() RETURNS VOID AS $$
BEGIN
    DELETE FROM dev_logs.request_logs 
    WHERE timestamp < NOW() - INTERVAL '7 days';
    
    DELETE FROM dev_analytics.performance_metrics 
    WHERE timestamp < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Development notifications
COMMENT ON DATABASE asoud_dev IS 'ASOUD Platform Development Database - Auto-configured for development with enhanced logging and monitoring';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'ASOUD Development Database initialized successfully!';
    RAISE NOTICE 'Development schemas created: dev_analytics, dev_logs, dev_cache';
    RAISE NOTICE 'Performance monitoring tables created and ready';
    RAISE NOTICE 'Development views and functions available';
END
$$;