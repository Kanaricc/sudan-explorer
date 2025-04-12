import abc
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import commentjson


@dataclass
class NodeId:
    typ: str
    id: str
    readable_id: Optional[str] = None
    description: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.typ, self.id))

    def to_dict(self) -> Dict[str, str]:
        """将 NodeId 转换为字典，便于 JSON 序列化"""
        return {
            "typ": self.typ,
            "id": self.id,
            "readable_id": self.readable_id if self.readable_id else "",
            "description": self.description if self.description else "",
        }

    def __repr__(self) -> str:
        return f"NodeId(typ='{self.typ}', id='{self.id}')"


class Node(abc.ABC):
    def __init__(self, typ: str, id: str):
        self.typ = typ
        self.id = id
        self._path = f"config/{self.typ}/{self.id}.json"
        with open(self._path, "r") as f:
            self.data = commentjson.load(f)

    @property
    def path(self) -> str:
        return self._path

    @property
    @abc.abstractmethod
    def readable_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def description(self) -> str: ...

    @abc.abstractmethod
    def get_children(self) -> list["Node"]: ...

    def __hash__(self):
        return hash((self.typ, self.id))


class Event(Node):
    def __init__(self, id: str):
        super().__init__("event", id)

    @property
    def readable_id(self) -> str:
        return self.data["text"]

    @property
    def description(self) -> str:
        return ""

    def get_children(self) -> list[Node]:
        res: list[Node] = []
        settlement = self.data["settlement"]
        for x in settlement:
            actions = x["action"]
            for k, v in actions.items():
                try:
                    res.extend(get_candidate_children_from_action(k, v))
                except ValueError as e:
                    print(f"Invalid action type: {k} in {self.path}")
                    raise e
                except Exception as e:
                    print(f"Error in {self.path}: {e}")
                    raise e
        return list(set(res))


class Rite(Node):
    def __init__(self, id: str):
        super().__init__("rite", id)

    @property
    def readable_id(self) -> str:
        return self.data["name"]

    @property
    def description(self) -> str:
        return self.data['text']

    def get_children(self) -> list[Node]:
        res: list[Node] = []
        settlement = self.data["settlement"]
        for x in settlement:
            actions = x["action"]
            for k, v in actions.items():
                try:
                    res.extend(get_candidate_children_from_action(k, v))
                except ValueError as e:
                    print(f"Invalid action type: {k} in {self.path}")
                    raise e
                except Exception as e:
                    print(f"Error in {self.path}: {e}")
                    raise e
        return list(set(res))


def build_node(typ: str, id: str) -> Node:
    if typ == "event":
        return Event(id)
    elif typ == "rite":
        return Rite(id)
    else:
        raise ValueError(f"unknown node type `{typ}`")


def get_candidate_children_from_action(k: str, v: Any) -> list[Node]:
    action_map = {
        "event_on": "event",
        "event_off": "event",
        "event": "event",
        "rite": "rite",
    }
    if k in action_map:
        node_type = action_map[k]
        if str(v) == "1":  # 一个全局事件
            return []
        if isinstance(v, list):
            return [build_node(node_type, str(x)) for x in v]
        else:
            # 特判
            if node_type == "event" and v == 5000515:
                node_type = "rite"
            if node_type == "rite" and v == 5320511:
                node_type = "event"
            return [build_node(node_type, str(v))]
    elif k.startswith("case:") or k in [
        "success",
        "failed",
        "choose",
        "all",
    ]:  # 成功时要触发的事件
        res: list[Node] = []
        for subk, subv in v.items():
            res.extend(get_candidate_children_from_action(subk, subv))
        return res
    elif k in ["option"]:
        return []  # 只是个 option
    elif k.startswith("global_counter") or k.startswith("counter"):
        return []  # 只是个 counter
    elif k in ["no_prompt", "prompt"]:
        return []  # 只是个增加卡牌的动作
    elif k.startswith("loot") or k in ["card"]:
        return []  # 随机卡牌事件
    elif k in ["over"]:
        return []  # 只是个结束的动作
    elif k in ["steam_achievement"]:
        return []  # 只是个 steam 成就
    elif k.startswith("clean."):
        return []  # 只是个清理仪式
    elif k in ["delay_off", "delay"]:
        return []  #
    elif k.startswith("table."):
        return []
    elif k.startswith("total."):
        return []
    elif k.startswith("sudan_pool."):
        return []
    elif k.startswith("focus."):
        return []
    elif k in ["enable_auto_gen_sudan_card"]:
        return []
    elif k in ["coin", "金币"]:
        return []
    elif (
        k.startswith("rite_pop")
        or k.startswith("hand_pop")
        or k.startswith("think_pop")
    ):
        return []  # 仅仅是提示 tip
    elif k in [
        "sleep",
        "no_show",
        "close_box",
        "hand_card_refresh",
        "magic_sudan",
        "debug",
        "begin_guide",
        "slide",
        "difficulty",
        "change_name",
        "confirm",
    ]:
        return []
    elif k.startswith("s1") or k.startswith("s2"):
        return []  # 无法判断这是干嘛用的，似乎是人物属性修改
    else:
        raise ValueError(f"Invalid action type: {k}")


vis: list[NodeId] = []
graph = []


def bfs(node: Node):
    global graph

    print(f"visiting {node.typ} {node.id}")
    queue = [node]
    while queue:
        node = queue.pop(0)
        if NodeId(node.typ, node.id) in vis:
            continue
        vis.append(NodeId(node.typ, node.id))
        # add to graph
        children = node.get_children()
        for child in children:
            graph.append(
                (
                    NodeId(node.typ, node.id, node.readable_id, node.description),
                    NodeId(child.typ, child.id, child.readable_id, child.description),
                )
            )

        queue.extend(children)


def walk_all_json(dir: str):
    global graph
    for dir, _, files in os.walk(dir):
        for file in files:
            if file.endswith(".json"):
                typ = dir.split("/")[-1]
                if typ not in ["event", "rite"]:
                    continue
                id = file.split(".")[0]

                node = build_node(typ, id)
                graph.append(
                    (
                        NodeId("event", "0"),
                        NodeId(typ, id, node.readable_id, node.description),
                    )
                )
                bfs(node)
    graph = list(set(graph))


def shuffle_event():
    global graph
    
    # 创建一个映射，记录每个 event 节点连接到的所有 rite 节点
    event_to_rites: Dict[NodeId, List[NodeId]] = {}
    
    # 第一步：找出所有 event 节点连接到的 rite 节点
    for source, target in graph:
        if target.typ == "event":
            if target not in event_to_rites:
                event_to_rites[target] = []
            
            # 使用 DFS 找出这个 event 节点连接到的所有 rite 节点
            def dfs(node_id: NodeId, visited: set) -> List[NodeId]:
                if node_id in visited:
                    return []
                visited.add(node_id)
                
                rites = []
                for s, t in graph:
                    if s == node_id:
                        if t.typ == "rite":
                            rites.append(t)
                        elif t.typ == "event" and t not in visited:
                            rites.extend(dfs(t, visited.copy()))
                return rites
            
            event_rites = dfs(target, set())
            event_to_rites[target].extend(event_rites)
    
    # 第二步：创建新的图，跳过 event 节点，直接连接到 rite 节点
    new_graph = []
    for source, target in graph:
        if target.typ == "rite":
            # 保留直接连接到 rite 的边
            new_graph.append((source, target))
        elif target.typ == "event":
            # 对于连接到 event 的边，创建直接连接到 rite 的新边
            for rite in event_to_rites[target]:
                new_graph.append((source, rite))
    
    # 去除重复的边
    graph = list(set(new_graph))


# 自定义 JSON 编码器，处理 NodeId 类型
class NodeIdEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, NodeId):
            return o.to_dict()
        # 处理元组，将其转换为列表
        if isinstance(o, tuple):
            return list(o)
        return super().default(o)


if __name__ == "__main__":
    walk_all_json("config")
    shuffle_event()
    with open("graph.json", "w") as f:
        json.dump(graph, f, ensure_ascii=False, indent=4, cls=NodeIdEncoder)
