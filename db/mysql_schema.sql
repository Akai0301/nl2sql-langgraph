-- MySQL Platform Database Schema
-- 用于存储平台数据：会话、查询历史、用户偏好等

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS nl2sql_platform DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE nl2sql_platform;

-- 会话表
CREATE TABLE IF NOT EXISTS chat_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) COMMENT '会话标题（首条问题自动生成）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- 问答对表（原 query_history，重构）
CREATE TABLE IF NOT EXISTS query_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL COMMENT '所属会话ID',
    question TEXT NOT NULL COMMENT '用户问题',
    generated_sql TEXT COMMENT '生成的 SQL',
    `columns` JSON COMMENT '结果列名',
    `rows` JSON COMMENT '结果数据',
    execution_error TEXT COMMENT '执行错误信息',
    is_favorite TINYINT(1) DEFAULT 0 COMMENT '是否收藏',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_favorite (is_favorite),
    FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答对记录表';

-- 用户偏好表（预留）
CREATE TABLE IF NOT EXISTS user_preferences (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) COMMENT '用户标识',
    preference_key VARCHAR(100) NOT NULL COMMENT '偏好键',
    preference_value TEXT COMMENT '偏好值',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_user_key (user_id, preference_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户偏好表';

-- AI 模型配置表
CREATE TABLE IF NOT EXISTS ai_model_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL COMMENT '配置名称',
    provider VARCHAR(50) NOT NULL COMMENT '提供商：openai/anthropic/deepseek/custom',
    base_url VARCHAR(255) COMMENT 'API Base URL',
    api_key TEXT COMMENT 'API Key',
    model_name VARCHAR(100) NOT NULL COMMENT '模型名称',
    is_active TINYINT(1) DEFAULT 0 COMMENT '是否激活',
    extra_params JSON COMMENT '额外参数（temperature、max_tokens等）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_config_name (config_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI模型配置表';

-- 数据源配置表
CREATE TABLE IF NOT EXISTS datasource_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ds_name VARCHAR(100) NOT NULL COMMENT '数据源名称',
    ds_type VARCHAR(20) NOT NULL COMMENT '类型：postgresql/mysql/sqlite',
    host VARCHAR(255) COMMENT '主机地址',
    port INT COMMENT '端口',
    `database` VARCHAR(100) COMMENT '数据库名',
    username VARCHAR(100) COMMENT '用户名',
    password TEXT COMMENT '密码',
    dsn_override TEXT COMMENT '完整 DSN（优先使用）',
    is_query_target TINYINT(1) DEFAULT 0 COMMENT '是否为问数查询目标',
    extra_params JSON COMMENT '额外连接参数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_ds_name (ds_name),
    INDEX idx_is_query_target (is_query_target)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据源配置表';

-- 知识库配置表
CREATE TABLE IF NOT EXISTS knowledge_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    datasource_id BIGINT NOT NULL COMMENT '所属数据源ID',
    kb_type VARCHAR(20) NOT NULL COMMENT '类型：term/qa/metric/table_desc',
    kb_name VARCHAR(100) NOT NULL COMMENT '知识项名称',
    kb_content TEXT COMMENT '知识内容（JSON格式）',
    kb_metadata JSON COMMENT '元数据（表名、字段名等）',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_datasource (datasource_id),
    INDEX idx_kb_type (kb_type),
    FOREIGN KEY (datasource_id) REFERENCES datasource_config(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库配置表';