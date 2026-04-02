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