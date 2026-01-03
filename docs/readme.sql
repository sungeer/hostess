
pip cache purge  # 清除缓存

pip freeze > requirements.txt
pip install -r requirements.txt




python -m pip install asyncmy httpx sqlalchemy starlette



# -------------------------
# App / State (Starlette-ish)
# -------------------------




CREATE TABLE task (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  task_name   VARCHAR(128) NOT NULL COMMENT '任务名',
  is_active   TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0关 1开',
  is_running  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0停止 1运行',
  is_deleted  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0未删 1已删',
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_task_name (task_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务配置';



CREATE TABLE task_runtime (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  task_id     BIGINT UNSIGNED NOT NULL,
  is_running  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0停止 1运行',
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运行状态';



CREATE TABLE config_switch (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  ctrl_key    VARCHAR(64) NOT NULL COMMENT '开关名',
  is_active   TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0关 1开',
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_ctrl_key (ctrl_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全局开关';


-- 初始化：允许运行
INSERT INTO system_control(control_key, control_value)
VALUES ('TASKS_GLOBALLY_ENABLED', '1')
ON DUPLICATE KEY UPDATE control_value='1';

-- 更通用为此次值
INSERT INTO system_control(control_key, control_value)
VALUES ('TASKS_GLOBALLY_ENABLED', '1')
ON DUPLICATE KEY UPDATE control_value = VALUES(control_value);


