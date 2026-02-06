# -*- coding: utf-8 -*-
"""
Builds a dependency-processing plan (topological order) *in levels*.
Outputs dependency_plan_levels_{organized_stem}.json
This is the required input for llm_conditional.py
"""

# use the v-codes only
# Use the same llm instance
# Hammer solution: agent models
# My system is a sinlge-use llm per chunk, which is not as efficent as
# commanding multiple child llms at the same time using a master command


import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

def topological_sort_levels(nodes: Set[str], edges: List[Tuple[str, str]]) -> List[List[str]]:
    """
    Performs a topological sort using Kahn's algorithm, organized by levels.
    Returns:
        A list of lists, where each inner list contains all nodes at that
        dependency level.
    """
    incoming_count: Dict[str, int] = {n: 0 for n in nodes}
    outgoing_edges: Dict[str, List[str]] = {n: [] for n in nodes}
    
    for a, b in edges:
        if a not in nodes or b not in nodes:
            continue
        outgoing_edges[a].append(b)
        incoming_count[b] += 1
        
    # Initialize the first level with all nodes having an in-degree of 0
    current_level_queue = [n for n, c in incoming_count.items() if c == 0]
    all_levels: List[List[str]] = []
    
    while current_level_queue:
        # Add the current level to our list of levels
        all_levels.append(current_level_queue)
        
        next_level_queue: List[str] = []
        for node in current_level_queue:
            for neighbor in outgoing_edges[node]:
                incoming_count[neighbor] -= 1
                if incoming_count[neighbor] == 0:
                    next_level_queue.append(neighbor)
        
        # Prepare for the next iteration
        current_level_queue = next_level_queue
        
    # Check for cycles (nodes not included in any level)
    nodes_in_levels = set(n for level in all_levels for n in level)
    if len(nodes_in_levels) != len(nodes):
        cycle_nodes = [n for n in nodes if n not in nodes_in_levels]
        print(f"Warning: Cycle detected! The following nodes are part of a cycle and will be added at the end:")
        print(f"{cycle_nodes}")
        all_levels.append(cycle_nodes) # Add them in a final level
        
    return all_levels


def build_processing_plan_levels(organized_path: str, dep_path: str, output_dir: str = ".") -> str:
    """
    Builds a level-based dependency plan from the organized questions and
    the dependency map.
    """
    with open(organized_path, "r", encoding="utf-8") as f:
        organized = json.load(f)
    with open(dep_path, "r", encoding="utf-8") as f:
        dep_map = json.load(f)

    nodes: Set[str] = set()
    for chunk_data in organized.get("chunks", {}).values():
        for q in chunk_data.get("questions", []):
            code = q.get("code") or q["id"]
            nodes.add(code)

    # Build edges parent -> child
    edges: List[Tuple[str, str]] = []
    for item in dep_map:
        child = item.get("question_code") or item.get("question_id")
        for parent in item.get("depends_on", []):
            if parent in nodes and child in nodes:
                edges.append((parent, child))

    # Generate the level-based topological sort
    ordered_levels = topological_sort_levels(nodes, edges)

    # Save the plan
    stem = Path(organized_path).stem
    out_path = Path(output_dir) / f"dependency_plan_levels_{stem}.json"
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ordered_levels, f, indent=2, ensure_ascii=False)

    print(f"Level-based dependency plan saved to {out_path}")
    print(f"Plan has {len(ordered_levels)} levels.")
    return str(out_path)


if __name__ == "__main__":
    # Ensure this matches the JSON file you are using
    organized_file = "organized_constitutional_questions.json"
    # Ensure this matches the output of extract_dependencies.py
    dependencies_file = "extract_dependencies/question_dependencies_organized_constitutional_questions.json"
    
    build_processing_plan_levels(
        organized_file, 
        dependencies_file, 
        output_dir="."
    )