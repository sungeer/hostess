
pip cache purge  # 清除缓存

pip freeze > requirements.txt
pip install -r requirements.txt




python -m pip install asyncmy httpx sqlalchemy starlette orjson uvicorn loguru



uvicorn demo:app --host 0.0.0.0 --port 8000


uvicorn demo:app --port 7788


# -------------------------
# App / State (Starlette-ish)
# -------------------------



-- 任务
CREATE TABLE task (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  task_name   VARCHAR(128) NOT NULL COMMENT '任务名',
  task_key    VARCHAR(128) NOT NULL COMMENT '任务键名',
  task_func   VARCHAR(128) NOT NULL COMMENT '函数名',
  doc_about   VARCHAR(255) NOT NULL COMMENT '文档相关',
  is_deleted  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0未删 1已删',
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_task_key (task_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务';


-- 持久化 启停 开关
CREATE TABLE switch (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  task_id     BIGINT UNSIGNED NOT NULL COMMENT 'task表ID',
  is_paused   TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0未暂停 1暂停',
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  KEY idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持久化启停开关';


-- 1) 插入 task
INSERT INTO task (task_name, task_key, task_func, doc_about, is_deleted)
VALUES ('测试', 'demo_a', 'tasks.demo_a.worker', '3.2', 0);


-- 2) 插入 switch（关联刚插入的 task.id）
INSERT INTO switch (task_id, is_paused)
VALUES (1, 0);


-- 异常记录



-- 操作记录



-- 订单
CREATE TABLE produce_item (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  assign_item_id   VARCHAR(255) NOT NULL COMMENT '订单明细ID',
  task_key         VARCHAR(128) NOT NULL COMMENT '任务键名',
  is_deleted       TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0未删 1已删',
  created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_assign_item_id (assign_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生产单';


-- 原始数据
CREATE TABLE in_raw (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  produce_item_id  VARCHAR(255) NOT NULL COMMENT 'produce_item表ID',
  payload          JSON NOT NULL COMMENT '原始数据',
  created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_produce_item_id (produce_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='原始数据';


-- 订单 有效字段 给台风用
CREATE TABLE produce_json (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  produce_item_id  VARCHAR(255) NOT NULL COMMENT 'produce_item表ID',
  payload          JSON NOT NULL COMMENT '有效字段',
  created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_produce_item_id (produce_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单有效数据';


-- 订单 接收 回执
CREATE TABLE produce_ack (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  produce_item_id  VARCHAR(255) NOT NULL COMMENT 'produce_item表ID',
  status           TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0=PEND,1=OK,2=RETRY,3=DEAD',
  retry_count      INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '重试次数,最多3次',
  created_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_produce_item_id (produce_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单接收回执';


