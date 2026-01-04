
pip cache purge  # 清除缓存

pip freeze > requirements.txt
pip install -r requirements.txt




python -m pip install asyncmy httpx sqlalchemy starlette orjson uvicorn loguru



uvicorn demo:app --host 0.0.0.0 --port 8000


uvicorn demo:app --port 7788


# -------------------------
# App / State (Starlette-ish)
# -------------------------




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

