-- MySQL initialization for the GFP CoreX scale stack.
-- Application tables are created by SQLAlchemy metadata on startup; this script
-- only guarantees the database exists with a sane charset and that the app user
-- (created from MYSQL_USER / MYSQL_PASSWORD) can reach it.

CREATE DATABASE IF NOT EXISTS gfp_prod_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON gfp_prod_db.* TO 'gfp_user'@'%';
FLUSH PRIVILEGES;
