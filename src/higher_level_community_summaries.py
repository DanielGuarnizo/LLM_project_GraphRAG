import os
import json
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

@dataclass
class HighLevelCommunitySummarizer:
    def __init__(
        self, 
        hierarchy: List[Dict],
        summary_root_dir: str,  
        model: str,  
        max_tokens: int = 8000  
    ):
        self.hierarchy = hierarchy
        self.summary_root_dir = summary_root_dir
        self.model = model
        self.max_tokens = max_tokens
        self.high_level_cs_llm = ChatOpenAI(model_name=model)

    def run(self, hierarchy: Optional[List[Dict]] = None, current_level: Optional[str] = None):
        if hierarchy is None:
            hierarchy = self.hierarchy

        key_name = next(iter(hierarchy[0].keys() - {"children"}))
        if current_level is None:
            current_level = key_name.split("_")[0]  # E.g., "C2"
        lower_level = f"C{int(current_level[1]) + 1}"

        print(f"\n📘 Processing summaries at level: {current_level} ({len(hierarchy)} communities)")

        for node in hierarchy:
            community_id_key = next(k for k in node if k != "children")
            community_id = node[community_id_key]
            children = node["children"]

            if isinstance(children[0], int):  # Leaf-level children
                self.summarize_group(
                    group_ids=children,
                    current_level=current_level,
                    output_community_id=community_id,
                    source_dir=os.path.join(self.summary_root_dir, lower_level),
                    dest_dir=os.path.join(self.summary_root_dir, current_level)
                )
            else:
                self.run(
                    hierarchy=children,
                    current_level=lower_level
                )
                self.summarize_group(
                    group_ids=[c[next(k for k in c if k != "children")] for c in children],
                    current_level=current_level,
                    output_community_id=community_id,
                    source_dir=os.path.join(self.summary_root_dir, lower_level),
                    dest_dir=os.path.join(self.summary_root_dir, current_level)
                )

    def summarize_group(
            self, group_ids: List[int], current_level: str, output_community_id: Union[str, int],
                    source_dir: str, dest_dir: str):
        out_path = os.path.join(dest_dir, f"{current_level}_{output_community_id}.json")
        if os.path.exists(out_path):
            print(f"⏭️ Skipping {current_level}_{output_community_id}, summary already exists at: {out_path}")
            return

        documents = []
        summaries = []
        total_tokens = 0

        for cid in group_ids:
            file_path = os.path.join(source_dir, f"{os.path.basename(source_dir)}_{cid}.json")
            if not os.path.exists(file_path):
                print(f"⚠️ Missing summary file: {file_path}")
                continue
            with open(file_path, "r") as f:
                data = json.load(f)

            try:
                tokens = data.get("tokens", 0)
                content = data.get("summary", data)
                if isinstance(content, dict) and "summary" in content:
                    summary_text = content["summary"]
                    findings = content.get("findings", [])
                    findings_text = "\n".join(f"- {f['summary']}" for f in findings)
                    doc_text = f"{summary_text}\n\nKey Findings:\n{findings_text}"
                else:
                    doc_text = str(content)

                summaries.append({
                    "id": cid,
                    "text": doc_text,
                    "tokens": tokens
                })
                total_tokens += tokens
            except Exception as e:
                print(f"❌ Error parsing {file_path}: {e}")
                continue

        if not summaries:
            print(f"❌ No valid summaries for {current_level}_{output_community_id}")
            return

        if total_tokens > self.max_tokens:
            print(f"⚠️ Token overflow ({total_tokens}), applying replacement strategy...")
            summaries.sort(key=lambda x: x["tokens"], reverse=True)
            replacement_text = [f"(Summary of Community {s['id']})" for s in summaries]
            running_total = 0
            selected = []

            for idx, s in enumerate(summaries):
                if running_total + len(replacement_text[idx]) > self.max_tokens:
                    break
                selected.append(replacement_text[idx])
                running_total += len(replacement_text[idx])

            final_input = "\n".join(selected)
        else:
            final_input = "\n\n".join([f"### Community {s['id']}\n{s['text']}" for s in summaries])

        system_prompt = """
        You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
        Given one or more entities, and a list of descriptions, all related to the same entity or group of entities.
        Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
        If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
        Make sure it is written in third person, and include the entity names so we have the full context.
        """
        human_prompt = f"""
        ---Real Data---
        Use the following data for your answer. Do not make anything up in your answer.
        Input:
        {final_input}
        Output:
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        try:
            response = self.high_level_cs_llm.invoke(messages)
            answer = response.content if hasattr(response, "content") else str(response)

            os.makedirs(dest_dir, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump({
                    "community_id": f"{current_level}_{output_community_id}",
                    "tokens": total_tokens,
                    "summary": answer
                }, f, indent=2)

            print(f"✅ Saved high-level summary: {out_path}")

        except Exception as e:
            print(f"❌ Failed to summarize {current_level}_{output_community_id}: {e}")
    