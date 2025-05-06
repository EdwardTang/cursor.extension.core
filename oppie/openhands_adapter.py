"""
Oppie - OpenHands Adapter

这个模块提供了Oppie与OpenHands ACI之间的适配和集成。
主要功能：
1. 将Template A转换为OpenHands任务
2. 将OpenHands事件转换为Oppie事件流
3. 配置和管理OpenHands运行时
"""

import os
import re
import json
import asyncio
from typing import Dict, List, Optional, Any, Union

# OpenHands导入
try:
    from openhands.core import Agent, Task, Event
    from openhands.core.config import AppConfig
    from openhands.core.events import Action, Observation
    from openhands.core.setup import setup_agent
    OPENHANDS_AVAILABLE = True
except ImportError:
    OPENHANDS_AVAILABLE = False
    # 定义适配器以防OpenHands不可用时允许代码编译
    class Agent: pass
    class Task: pass
    class Event: pass
    class AppConfig: pass
    class Action: pass
    class Observation: pass
    
    def setup_agent(*args, **kwargs):
        raise ImportError("OpenHands not available")

# Template A正则表达式
TEMPLATE_A_REGEX = re.compile(r"## Template A(\d+)")
CYCLE_REGEX = re.compile(r"\[🔢 CYCLE_NUMBER\]\s+(\d+)")
GOAL_REGEX = re.compile(r"\[🎯 NEXT GOAL \(Cycle (\d+)\)\]([^\[]+)")

class OpenHandsAdapter:
    """
    OpenHands与Oppie集成的主适配器类
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化OpenHands适配器
        
        Args:
            config_path: OpenHands配置文件路径，如果为None则使用默认配置
        """
        self.enabled = os.environ.get("OPENHANDS_ENABLED", "false").lower() == "true"
        self.agent = None
        self.template_adapter = None
        
        if self.enabled and OPENHANDS_AVAILABLE:
            self._initialize_openhands(config_path)
        else:
            print("OpenHands integration disabled or package not available")
    
    def _initialize_openhands(self, config_path: Optional[str] = None):
        """初始化OpenHands agent和配置"""
        config = self._load_config(config_path)
        self.agent = setup_agent(config)
        self.template_adapter = TemplateAAdapter(self.agent)
        
        # 注册事件处理器
        self._register_event_handlers()
    
    def _load_config(self, config_path: Optional[str]) -> AppConfig:
        """加载OpenHands配置"""
        if config_path and os.path.exists(config_path):
            return AppConfig.from_toml(config_path)
        
        # 默认配置
        return AppConfig(
            core={
                "mode": "headless",
                "agent": "code_act_agent"
            },
            llm={
                "provider": "openai",
                "model": "gpt-4"
            },
            runtime={
                "type": "local",
                "isolation": "minimal"
            },
            security={
                "allow_file_operations": True,
                "allow_command_execution": True
            },
            budget={
                "max_tool_calls": 24,
                "action_delay_ms": 100
            },
            vector_store={
                "type": "faiss",
                "path": "./.openhands/vectors"
            }
        )
    
    def _register_event_handlers(self):
        """注册OpenHands事件处理器"""
        if not self.agent:
            return
            
        # 监听工具调用超出限制事件
        self.agent.on("budget_exceeded", self._handle_budget_exceeded)
        
        # 监听所有事件以进行记录和转发
        self.agent.on("action", self._handle_action)
        self.agent.on("observation", self._handle_observation)
    
    def _handle_budget_exceeded(self, event: Event):
        """处理预算超出事件"""
        print(f"OpenHands budget exceeded: {event}")
        # 此处可以触发恢复机制
    
    def _handle_action(self, action: Action):
        """处理动作事件并转发"""
        # 将OpenHands Action转换为Oppie事件并发送到UI
        event = self._convert_to_oppie_event(action)
        self._send_event(event)
    
    def _handle_observation(self, observation: Observation):
        """处理观察事件并转发"""
        # 将OpenHands Observation转换为Oppie事件并发送到UI
        event = self._convert_to_oppie_event(observation)
        self._send_event(event)
    
    def _convert_to_oppie_event(self, oh_event: Union[Action, Observation]) -> Dict:
        """将OpenHands事件转换为Oppie事件格式"""
        # 这里实现转换逻辑
        return {
            "type": "openhands_event",
            "payload": {
                "id": getattr(oh_event, "id", "unknown"),
                "type": oh_event.__class__.__name__,
                "timestamp": getattr(oh_event, "timestamp", 0),
                "data": getattr(oh_event, "data", {}),
                # 其他需要的字段
            }
        }
    
    def _send_event(self, event: Dict):
        """发送事件到UI和其他监听器"""
        # 实际发送逻辑将在集成时实现
        print(f"Event: {json.dumps(event)}")
    
    async def execute_task(self, template_text: str) -> Dict:
        """
        执行OpenHands任务
        
        Args:
            template_text: Template A文本
            
        Returns:
            执行结果
        """
        if not self.enabled or not OPENHANDS_AVAILABLE or not self.agent:
            return {"error": "OpenHands integration disabled or not available"}
        
        try:
            # 将Template A转换为OpenHands任务
            task = self.template_adapter.convert_template_to_task(template_text)
            
            # 执行任务
            result = await self.agent.execute(task)
            
            return {
                "success": True,
                "task_id": task.id,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """检查OpenHands集成是否可用"""
        return self.enabled and OPENHANDS_AVAILABLE and self.agent is not None


class TemplateAAdapter:
    """Template A与OpenHands任务相互转换的适配器"""
    
    def __init__(self, agent: Agent):
        """
        初始化Template A适配器
        
        Args:
            agent: OpenHands代理实例
        """
        self.agent = agent
    
    def convert_template_to_task(self, template_text: str) -> Task:
        """
        将Template A文本转换为OpenHands任务
        
        Args:
            template_text: Template A格式的文本
            
        Returns:
            OpenHands Task对象
        """
        # 解析循环号
        cycle_match = CYCLE_REGEX.search(template_text)
        cycle = int(cycle_match.group(1)) if cycle_match else 0
        
        # 解析目标
        goal_match = GOAL_REGEX.search(template_text)
        goal = goal_match.group(2).strip() if goal_match else ""
        
        # 创建OpenHands任务
        return Task(
            type="code",
            instructions=template_text,
            metadata={
                "cycle": cycle,
                "goal": goal,
                "type": "template_a",
                "executor": "cursor"
            }
        )
    
    def convert_events_to_template(self, events: List[Event], cycle: int) -> str:
        """
        将OpenHands事件集合转换回Template A格式
        
        Args:
            events: OpenHands事件列表
            cycle: 当前循环号
            
        Returns:
            下一个Template A文本
        """
        # 构建下一个Template A
        # 这里需要实现完整的Template A构建逻辑
        # 由于逻辑复杂，此处仅提供骨架
        
        template = f"""## Template A{cycle+1} — Plan-and-Execute Cycle

---
#### 📈 CYCLE {cycle+1} CONTEXT (filled by Executor, served to Planner)

[🔢 CYCLE_NUMBER]     {cycle+1}
[📂 PROJECT]          Oppie.xyz 远程Cursor控制网络
[🗺️ PREVIOUS GOAL (Cycle {cycle})] {self._extract_goal_from_events(events, cycle)}
[✅ PREVIOUS OUTCOME (Cycle {cycle})] {self._extract_outcome_from_events(events)}
[🚧 CURRENT BLOCKERS] {self._extract_blockers_from_events(events)}
[🎯 NEXT GOAL (Cycle {cycle+1})] {self._suggest_next_goal(events, cycle)}
[📜 HISTORY PATH]      .specstory/history/openhands-integration.md
[⏳ TIME BOX]          4小时
[📎 RELEVANT ARTIFACTS] {self._extract_artifacts_from_events(events)}
[🗒️ SCRATCHPAD DELTA] {self._extract_scratchpad_delta(events)}
[🔍 AVAILABLE MCP TOOLS] .cursor/available_mcp_tools.md
[🔖 ADR LINK] .cursor/adr/20250506_openhands_aci.md
---
#### 📞 EXECUTOR ➡️ PLANNER QUESTIONS / REQUESTS (optional, filled by Executor)
[❓ ANALYSIS & JUSTIFICATION] 
[❓ PLAN] 
[❓ BLOCKER SOLUTIONS] 
[❓ BEST PRACTICES /MENTAL MODELS] 
[❓ MCP TOOLS] 
---
#### 📝 PLANNER RESPONSE FOR CYCLE {cycle+1} (filled by Planner, shipped to Executor)
"""
        return template
    
    def _extract_goal_from_events(self, events: List[Event], cycle: int) -> str:
        """从事件中提取上一个循环的目标"""
        # 实现从事件中提取目标的逻辑
        return "[从事件中提取的目标]"
    
    def _extract_outcome_from_events(self, events: List[Event]) -> str:
        """从事件中提取执行结果"""
        # 实现从事件中提取执行结果的逻辑
        return "[从事件中提取的执行结果]"
    
    def _extract_blockers_from_events(self, events: List[Event]) -> str:
        """从事件中提取阻塞问题"""
        # 实现从事件中提取阻塞问题的逻辑
        return "[从事件中提取的阻塞问题]"
    
    def _suggest_next_goal(self, events: List[Event], cycle: int) -> str:
        """根据当前事件建议下一个目标"""
        # 实现建议下一个目标的逻辑
        return "[建议的下一个目标]"
    
    def _extract_artifacts_from_events(self, events: List[Event]) -> str:
        """从事件中提取相关资源"""
        # 实现从事件中提取相关资源的逻辑
        return "[从事件中提取的相关资源]"
    
    def _extract_scratchpad_delta(self, events: List[Event]) -> str:
        """从事件中提取scratchpad变化"""
        # 实现从事件中提取scratchpad变化的逻辑
        return "[从事件中提取的scratchpad变化]"


# 用于测试的简单示例
if __name__ == "__main__":
    # 测试适配器
    adapter = OpenHandsAdapter()
    print(f"OpenHands available: {adapter.is_available()}") 