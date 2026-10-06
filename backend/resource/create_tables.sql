-- SQLite 数据库结构
-- 部门表定义

CREATE TABLE "departments" (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT NOT NULL, -- 部门名称
  `parent_id` INTEGER, -- 上级部门ID
  `manager_id` INTEGER, -- 部门负责人ID
  `create_time` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 创建时间
  `edit_time` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP -- 更新时间
);

CREATE UNIQUE INDEX uniq_department_name ON departments (name);

-- 员工表定义

CREATE TABLE `employees` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `employee_id` TEXT NOT NULL, -- 员工编号
  `name` TEXT NOT NULL, -- 姓名
  `phone` TEXT NOT NULL, -- 联系电话
  `email` TEXT NOT NULL, -- 电子邮箱
  `department_id` INTEGER NOT NULL, -- 所属部门
  `position` TEXT NOT NULL, -- 当前职位
  `hire_date` TEXT NOT NULL, -- 入职日期
  `create_time` TEXT DEFAULT CURRENT_TIMESTAMP, -- 创建时间
  `edit_time` TEXT DEFAULT CURRENT_TIMESTAMP -- 更新时间
);

CREATE UNIQUE INDEX `uniq_employee_id` ON `employees` (`employee_id`);
