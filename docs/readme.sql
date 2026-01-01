
pip cache purge  # 清除缓存

pip freeze > requirements.txt
pip install -r requirements.txt




python -m pip install asyncmy httpx sqlalchemy



# -------------------------
# App / State (Starlette-ish)
# -------------------------




CREATE TABLE switch (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  task_name VARCHAR(128) NOT NULL COMMENT '任务名',
  status TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0关 1开',
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '0未删 1已删',
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

  PRIMARY KEY (id),
  UNIQUE KEY uk_task_name (task_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='开关控制表';




