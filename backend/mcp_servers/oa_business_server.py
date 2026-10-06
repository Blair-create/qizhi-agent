"""通过 MCP 提供基于 SQLite 的员工与请假业务工具。"""
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "resource" / "database.db"
mcp = FastMCP("oa-business")

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    # 删除旧的单数命名表；运行时统一读写 resource/generate_data.py
    # 生成的复数命名表结构。
    c.execute("DROP TABLE IF EXISTS employee")
    c.execute("DROP TABLE IF EXISTS department")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS leave_requests (
      id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT UNIQUE NOT NULL,
      employee_name TEXT NOT NULL, leave_type TEXT NOT NULL, start_date TEXT NOT NULL,
      end_date TEXT NOT NULL, days INTEGER NOT NULL, reason TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS employee_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, employee_id TEXT,
      details TEXT NOT NULL, created_at TEXT NOT NULL
    );
    """)
    c.commit(); return c

@mcp.tool()
async def query_employees(keyword: str = "") -> list[dict]:
    """查询员工，可按姓名、工号、部门或职位筛选。"""
    c=db(); q=f"%{keyword}%"; rows=c.execute("SELECT * FROM employees WHERE ?='' OR name LIKE ? OR employee_id LIKE ? OR position LIKE ?", (keyword,q,q,q)).fetchall(); c.close(); return [dict(r) for r in rows]

@mcp.tool()
async def get_all_user_info() -> list[dict]:
    """查询全部员工信息。统一从 employees 表读取。"""
    return await query_employees("")

@mcp.tool()
async def get_user_info(user_name: str) -> dict:
    """按姓名或工号查询员工信息，统一从 employees 表读取。"""
    rows = await query_employees(user_name)
    exact = [row for row in rows if row.get("name") == user_name or row.get("employee_id") == user_name]
    return exact[0] if exact else (rows[0] if rows else {"error": "未找到该员工"})

@mcp.tool()
async def get_user_department(user_name: str) -> dict:
    """查询员工所属部门，统一从 employees/departments 表读取。"""
    employee = await get_user_info(user_name)
    if "error" in employee:
        return employee
    c = db(); row = c.execute("SELECT * FROM departments WHERE id=?", (employee.get("department_id"),)).fetchone(); c.close()
    return dict(row) if row else {"error": "未找到该部门"}

@mcp.tool()
async def query_departments(keyword: str = "") -> list[dict]:
    """查询部门列表和部门 ID，新增员工前可先使用。"""
    c=db(); q=f"%{keyword}%"; rows=c.execute("SELECT * FROM departments WHERE ?='' OR name LIKE ?", (keyword,q)).fetchall(); c.close(); return [dict(r) for r in rows]

@mcp.tool()
async def add_employee(name: str, employee_id: str, department_id: int, position: str, hire_date: str, email: str = "", phone: str = "") -> dict:
    """新增员工并写入 SQLite。日期格式 YYYY-MM-DD。"""
    c=db(); now=datetime.now(timezone.utc).isoformat()
    try:
        c.execute("INSERT INTO employees(name,employee_id,department_id,position,hire_date,email,phone,created_at) VALUES(?,?,?,?,?,?,?,?)", (name,employee_id,department_id,position,hire_date,email,phone,now)); c.execute("INSERT INTO employee_audit(action,employee_id,details,created_at) VALUES(?,?,?,?)", ("add",employee_id,name,now)); c.commit(); return {"status":"created","employee_id":employee_id,"name":name}
    except sqlite3.IntegrityError as e: c.rollback(); raise ValueError(f"员工工号已存在或数据无效: {e}")
    finally: c.close()

@mcp.tool()
async def update_employee(employee_id: str, field: str, value: str) -> dict:
    """修改员工的允许字段：name、department_id、position、hire_date、email、phone。"""
    allowed={"name","department_id","position","hire_date","email","phone"}
    if field not in allowed: raise ValueError("不允许修改该字段")
    c=db(); now=datetime.now(timezone.utc).isoformat(); cur=c.execute(f"UPDATE employees SET {field}=? WHERE employee_id=?", (value,employee_id))
    if cur.rowcount==0: c.close(); raise ValueError("未找到员工")
    c.execute("INSERT INTO employee_audit(action,employee_id,details,created_at) VALUES(?,?,?,?)", ("update",employee_id,f"{field}={value}",now)); c.commit(); c.close(); return {"status":"updated","employee_id":employee_id,"field":field,"value":value}

@mcp.tool()
async def delete_employee(employee_id: str) -> dict:
    """删除员工并记录审计日志。"""
    c=db(); now=datetime.now(timezone.utc).isoformat(); cur=c.execute("DELETE FROM employees WHERE employee_id=?",(employee_id,))
    if cur.rowcount==0: c.close(); raise ValueError("未找到员工")
    c.execute("INSERT INTO employee_audit(action,employee_id,details,created_at) VALUES(?,?,?,?)",("delete",employee_id,"",now)); c.commit(); c.close(); return {"status":"deleted","employee_id":employee_id}

@mcp.tool()
async def create_leave_request(employee_name: str, leave_type: str, start_date: str, end_date: str, reason: str) -> dict:
    """创建请假申请，写入 SQLite 并进入 pending 审批状态。"""
    start=date.fromisoformat(start_date); end=date.fromisoformat(end_date)
    if end < start: raise ValueError("结束日期不能早于开始日期")
    request_id=f"LV-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"; now=datetime.now(timezone.utc).isoformat(); c=db()
    c.execute("INSERT INTO leave_requests(request_id,employee_name,leave_type,start_date,end_date,days,reason,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(request_id,employee_name,leave_type,start_date,end_date,(end-start).days+1,reason,"pending",now,now)); c.commit(); c.close()
    return {"status":"pending","request_id":request_id,"employee_name":employee_name,"days":(end-start).days+1}

@mcp.tool()
async def query_leave_requests(employee_name: str = "", status: str = "") -> list[dict]:
    """查询请假申请和审批状态。"""
    c=db(); rows=c.execute("SELECT * FROM leave_requests WHERE (?='' OR employee_name=?) AND (?='' OR status=?) ORDER BY id DESC",(employee_name,employee_name,status,status)).fetchall(); c.close(); return [dict(r) for r in rows]

@mcp.tool()
async def approve_leave_request(request_id: str, decision: str, comment: str = "") -> dict:
    """审批请假申请，decision 只能是 approved 或 rejected。"""
    if decision not in {"approved","rejected"}: raise ValueError("decision 必须是 approved 或 rejected")
    c=db(); now=datetime.now(timezone.utc).isoformat(); cur=c.execute("UPDATE leave_requests SET status=?,updated_at=? WHERE request_id=?",(decision,now,request_id))
    if cur.rowcount==0: c.close(); raise ValueError("未找到请假申请")
    c.commit(); row=c.execute("SELECT * FROM leave_requests WHERE request_id=?",(request_id,)).fetchone(); c.close(); return dict(row)

if __name__ == "__main__": mcp.run(transport="stdio")
