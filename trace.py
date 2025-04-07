import argparse
from dataclasses import dataclass
import os
import sys
from pathlib import Path
from typing import Any, List, Literal, Set
import commentjson
import fire



@dataclass
class NodeId:
    typ:str
    id:str

    def __hash__(self):
        return hash((self.typ,self.id))

def get_path(id:NodeId):
    # 使用应用程序运行目录作为基准，而不是 PyInstaller 的临时目录
    base_dir = Path(os.path.abspath(os.path.dirname(os.path.abspath(sys.argv[0]))))
    return str(base_dir / f"config/{id.typ}/{id.id}.json")

def read_json(id:NodeId):
    with open(get_path(id),"r") as f:
        x=commentjson.load(f)
    return x

def print_description(typ:str,data:Any):
    if typ=="event":
        pass
    elif typ=="rite":
        print(data["text"])

def get_readable_id(typ:str,data:Any):
    if typ=="event":
        return data["text"]
    elif typ=='rite':
        return data['name']
    else:
        raise ValueError(f"Invalid type: {typ}")
    
def get_candidate_children_from_action(k:str,v:Any):
    action_map={
        "event_on":"event",
        "rite":"rite",
    }
    if k in action_map:
        return [NodeId(action_map[k],str(v))]
    elif k in ["option"]:
        return []
    elif k.startswith('global_counter='):
        return []
    elif k.startswith("case:"):
        res:list[NodeId]=[]
        for subk,subv in v.items():
            if subk in action_map:
                res.append(NodeId(action_map[subk],str(subv)))
        return res
    else:
        print(f"\033[91mInvalid action type: {k}\033[0m")
        return []

def get_children(typ:str,data:Any):
    res:list[NodeId]=[]
    if typ=="event":
        settlement=data["settlement"]
        for x in settlement:
            actions=x['action']
            for k,v in actions.items():
                res.extend(get_candidate_children_from_action(k,v))
    elif typ=="rite":
        settlement=data["settlement"]
        for x in settlement:
            actions=x['action']
            for k,v in actions.items():
                res.extend(get_candidate_children_from_action(k,v))
    else:
        raise ValueError(f"Invalid type: {typ}")
    return list(set(res))

road:list[str]=[]

def trace(cur_id:NodeId,fa_id:NodeId):
    cur=read_json(cur_id)
    road.append(get_readable_id(cur_id.typ,cur))
    
    children=get_children(cur_id.typ,cur)
    
    
    while True:
        print("")
        print(f"===== {cur_id.typ} {cur_id.id} {get_readable_id(cur_id.typ,cur)}=====")
        print(get_path(cur_id),end='\t')
        print("->".join(road))
        print_description(cur_id.typ,cur)
        print("下步可激活：")
        for i,child in enumerate(children):
            print(f"{i}: {child.typ}\t{child.id}\t{get_readable_id(child.typ,read_json(child))}\t{get_path(child)}")
            print_description(child.typ,read_json(child))
            print("")
            
        opt=input("输入操作 (数字选择,留空返回)：")
        if opt=="":
            break
        elif opt.isdigit():
            opt=int(opt)
            if 0<=opt<len(children):
                trace(children[opt],cur_id)
            else:
                print("无效操作，请重新输入")
        else:
            print("无效操作，请重新输入")
    
    road.pop()




def search_file_content(file_path: Path, keyword: str) -> bool:
    """在文件内容中搜索关键字

    Args:
        file_path: 文件路径
        keyword: 要搜索的关键字（不区分大小写）

    Returns:
        bool: 如果找到关键字则返回True，否则返回False
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            return keyword.lower() in content
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read().lower()
                return keyword.lower() in content
        except Exception as e:
            print(f"警告: 无法读取文件 {file_path}: {e}")
            return False
    except Exception as e:
        print(f"错误: 处理文件 {file_path} 时出错: {e}")
        return False


def search_json_files(directory: Path, keyword: str) -> List[Path]:
    """搜索目录中包含关键字的JSON文件

    Args:
        directory: 要搜索的目录
        keyword: 要搜索的关键字

    Returns:
        List[Path]: 包含关键字的JSON文件路径列表
    """
    matching_files: List[Path] = []
    processed_files: Set[Path] = set()
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = Path(root) / file
                
                # 避免处理重复文件
                if file_path in processed_files:
                    continue
                processed_files.add(file_path)
                
                if search_file_content(file_path, keyword):
                    matching_files.append(file_path)
    
    return matching_files


def start_trace(typ: str, id: str) -> None:
    """启动 trace 功能
    
    Args:
        typ: 节点类型
        id: 节点ID
    """
    start_id = NodeId(typ, id)
    trace(start_id, NodeId("", ""))

def search(keyword: str, directory: str = 'config') -> None:
    """搜索功能
    
    Args:
        keyword: 要搜索的关键字
        directory: 要搜索的目录，默认为config
    """
    # 构建目录路径
    base_dir = Path(__file__).parent
    search_dir = base_dir / directory
    
    if not search_dir.exists() or not search_dir.is_dir():
        print(f"错误: 目录 {search_dir} 不存在或不是一个有效的目录")
        return
    
    print(f"正在搜索目录 {search_dir} 中包含关键字 '{keyword}' 的JSON文件...")
    matching_files = search_json_files(search_dir, keyword)
    
    if matching_files:
        print(f"\n找到 {len(matching_files)} 个匹配的文件:")
        for id, file_path in enumerate(matching_files):
            # 显示相对于项目根目录的路径
            rel_path = file_path.relative_to(base_dir)
            print(f"{id} - {rel_path}")
            if input("要直接开始追踪吗？(y/n)") == 'y':
                typ, id = rel_path.parts[-2:]
                start_trace(typ, id.split('.')[0])
        

    else:
        print(f"\n未找到包含关键字 '{keyword}' 的JSON文件")

def main() -> None:
    """主函数，处理命令行参数并执行搜索或trace"""
    parser = argparse.ArgumentParser(description='Sudan Cards 工具 - 搜索或追踪JSON文件')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 添加搜索子命令
    search_parser = subparsers.add_parser('search', help='搜索JSON文件')
    search_parser.add_argument('keyword', help='要搜索的关键字')
    search_parser.add_argument('--dir', '-d', default='config', help='要搜索的目录，默认为config')
    
    # 添加trace子命令
    trace_parser = subparsers.add_parser('trace', help='追踪节点关系')
    trace_parser.add_argument('type', help='节点类型，如event或rite')
    trace_parser.add_argument('id', help='节点ID')
    
    args = parser.parse_args()
    
    if args.command == 'search':
        search(args.keyword, args.dir)
    elif args.command == 'trace':
        start_trace(args.type, args.id)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()