"""
数据生成脚本 - 生成生产级测试数据
生成500+员工记录和50+部门层级结构
"""
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# 中文姓名库
SURNAMES = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周', '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '高', '罗']
GIVEN_NAMES = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀英', '华', '鹏']

# 部门结构
DEPARTMENTS = [
    {"name": "技术中心", "parent": None, "children": [
        {"name": "前端开发部", "parent": "技术中心", "children": [
            {"name": "Web前端组", "parent": "前端开发部"},
            {"name": "移动端开发组", "parent": "前端开发部"},
            {"name": "UI/UX设计组", "parent": "前端开发部"}
        ]},
        {"name": "后端开发部", "parent": "技术中心", "children": [
            {"name": "Java开发组", "parent": "后端开发部"},
            {"name": "Python开发组", "parent": "后端开发部"},
            {"name": "Go开发组", "parent": "后端开发部"}
        ]},
        {"name": "测试部", "parent": "技术中心", "children": [
            {"name": "功能测试组", "parent": "测试部"},
            {"name": "自动化测试组", "parent": "测试部"},
            {"name": "性能测试组", "parent": "测试部"}
        ]},
        {"name": "运维部", "parent": "技术中心", "children": [
            {"name": "系统运维组", "parent": "运维部"},
            {"name": "数据库运维组", "parent": "运维部"},
            {"name": "网络运维组", "parent": "运维部"}
        ]},
        {"name": "架构部", "parent": "技术中心", "children": [
            {"name": "系统架构组", "parent": "架构部"},
            {"name": "数据架构组", "parent": "架构部"}
        ]}
    ]},
    {"name": "产品中心", "parent": None, "children": [
        {"name": "产品管理部", "parent": "产品中心", "children": [
            {"name": "C端产品组", "parent": "产品管理部"},
            {"name": "B端产品组", "parent": "产品管理部"}
        ]},
        {"name": "用户研究部", "parent": "产品中心"}
    ]},
    {"name": "市场营销中心", "parent": None, "children": [
        {"name": "市场策划部", "parent": "市场营销中心"},
        {"name": "品牌推广部", "parent": "市场营销中心"},
        {"name": "渠道销售部", "parent": "市场营销中心", "children": [
            {"name": "华东区", "parent": "渠道销售部"},
            {"name": "华南区", "parent": "渠道销售部"},
            {"name": "华北区", "parent": "渠道销售部"}
        ]}
    ]},
    {"name": "职能中心", "parent": None, "children": [
        {"name": "人力资源部", "parent": "职能中心", "children": [
            {"name": "招聘组", "parent": "人力资源部"},
            {"name": "培训组", "parent": "人力资源部"},
            {"name": "薪酬福利组", "parent": "人力资源部"}
        ]},
        {"name": "财务部", "parent": "职能中心", "children": [
            {"name": "会计组", "parent": "财务部"},
            {"name": "出纳组", "parent": "财务部"}
        ]},
        {"name": "行政部", "parent": "职能中心"},
        {"name": "法务部", "parent": "职能中心"}
    ]}
]

POSITIONS = [
    "高级工程师", "工程师", "初级工程师", "资深工程师", "技术专家",
    "产品经理", "高级产品经理", "产品总监",
    "设计师", "高级设计师", "设计主管",
    "测试工程师", "高级测试工程师",
    "运维工程师", "高级运维工程师",
    "项目经理", "技术经理", "部门经理", "总监", "VP"
]

def flatten_departments(dept_tree, parent_id=None, result=None):
    """将树形部门结构展平"""
    if result is None:
        result = []
    
    for dept in dept_tree:
        dept_data = {
            "name": dept["name"],
            "parent_id": parent_id,
            "description": f"{dept['name']}负责相关业务"
        }
        result.append(dept_data)
        current_id = len(result)
        
        if "children" in dept:
            flatten_departments(dept["children"], current_id, result)
    
    return result

def generate_employees(num_employees=500):
    """生成员工数据"""
    employees = []
    base_date = datetime(2020, 1, 1)
    
    for i in range(num_employees):
        surname = random.choice(SURNAMES)
        given_name = random.choice(GIVEN_NAMES)
        name = surname + given_name + (str(random.randint(1, 99)) if random.random() > 0.7 else "")
        
        hire_date = base_date + timedelta(days=random.randint(0, 1800))
        
        employee = {
            "name": name,
            "employee_id": f"EMP{str(i+1).zfill(5)}",
            "department_id": random.randint(1, 50),
            "position": random.choice(POSITIONS),
            "hire_date": hire_date.strftime("%Y-%m-%d"),
            "email": f"{name.lower()}.{i+1}@company.com",
            "phone": f"138{random.randint(10000000, 99999999)}"
        }
        employees.append(employee)
    
    return employees

def create_database(db_path: str):
    """创建并填充数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 删除旧表
    cursor.execute("DROP TABLE IF EXISTS employees")
    cursor.execute("DROP TABLE IF EXISTS departments")
    
    # 创建部门表
    cursor.execute("""
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES departments(id)
        )
    """)
    
    # 创建员工表
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            employee_id TEXT UNIQUE NOT NULL,
            department_id INTEGER,
            position TEXT,
            hire_date DATE,
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)
    
    # 插入部门数据
    departments = flatten_departments(DEPARTMENTS)
    print(f"生成 {len(departments)} 个部门")
    
    for dept in departments:
        cursor.execute("""
            INSERT INTO departments (name, parent_id, description)
            VALUES (?, ?, ?)
        """, (dept["name"], dept["parent_id"], dept["description"]))
    
    # 插入员工数据
    employees = generate_employees(520)  # 生成520个员工
    print(f"生成 {len(employees)} 名员工")
    
    for emp in employees:
        cursor.execute("""
            INSERT INTO employees (name, employee_id, department_id, position, 
                                 hire_date, email, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (emp["name"], emp["employee_id"], emp["department_id"], 
              emp["position"], emp["hire_date"], emp["email"], emp["phone"]))
    
    conn.commit()
    
    # 验证数据
    cursor.execute("SELECT COUNT(*) FROM departments")
    dept_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM employees")
    emp_count = cursor.fetchone()[0]
    
    print(f"\n数据库创建完成:")
    print(f"- 部门总数: {dept_count}")
    print(f"- 员工总数: {emp_count}")
    
    # 显示统计信息
    cursor.execute("""
        SELECT d.name, COUNT(e.id) as employee_count
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id
        GROUP BY d.id, d.name
        ORDER BY employee_count DESC
        LIMIT 10
    """)
    
    print("\n员工最多的10个部门:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}人")
    
    conn.close()
    return dept_count, emp_count

if __name__ == "__main__":
    db_path = Path(__file__).parent / "database.db"
    print(f"数据库路径: {db_path}")
    dept_count, emp_count = create_database(str(db_path))
    print(f"\n✅ 成功生成 {dept_count} 个部门和 {emp_count} 名员工")

