-- 与本项目根目录 .env 中的 DB_USER / DB_PASSWORD / DB_NAME 一致（专用账号，不设 root 应用密码）
-- 用法（示例）：mysql -u root -p < scripts/init_mysql_aitest.sql

CREATE DATABASE IF NOT EXISTS ai_test_product CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'aitest'@'localhost' IDENTIFIED BY 'aitest';
GRANT ALL PRIVILEGES ON ai_test_product.* TO 'aitest'@'localhost';

CREATE USER IF NOT EXISTS 'aitest'@'127.0.0.1' IDENTIFIED BY 'aitest';
GRANT ALL PRIVILEGES ON ai_test_product.* TO 'aitest'@'127.0.0.1';

FLUSH PRIVILEGES;
