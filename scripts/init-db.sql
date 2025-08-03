-- Database initialization script for GFP CoreX
-- This script creates the necessary databases for different configurations

-- Create production database
CREATE DATABASE prod_db;
GRANT ALL PRIVILEGES ON DATABASE prod_db TO gfp_user;

-- Create development database
CREATE DATABASE dev_db;
GRANT ALL PRIVILEGES ON DATABASE dev_db TO gfp_user;

-- Create test database
CREATE DATABASE test_db;
GRANT ALL PRIVILEGES ON DATABASE test_db TO gfp_user;

-- Create additional databases for other configurations
CREATE DATABASE health_db;
GRANT ALL PRIVILEGES ON DATABASE health_db TO gfp_user;

CREATE DATABASE example_db;
GRANT ALL PRIVILEGES ON DATABASE example_db TO gfp_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gfp_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gfp_user; 