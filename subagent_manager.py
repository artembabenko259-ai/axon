from __future__ import annotations

import asyncio
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_client import LLMManager
from agent_manager import create_agent, load_agent_prompt, sanitize_agent_name

logger = logging.getLogger(__name__)


@dataclass
class SubagentInstance:
    conversation_id: str
    name: str
    prompt: str
    workspace_mode: str
    workspace_path: Path
    status: str = "running"  # running, completed, failed, killed
    messages: list[dict[str, Any]] = field(default_factory=list)
    task: asyncio.Task[Any] | None = None
    inbox: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    llm: LLMManager | None = None


class SubagentManager:
    def __init__(self, default_workspace: Path | None = None) -> None:
        self.workspace = default_workspace or Path.cwd()
        self.definitions: dict[str, dict[str, str]] = {}
        self.instances: dict[str, SubagentInstance] = {}

    def define_subagent(self, name: str, system_prompt: str, description: str) -> str:
        sanitized = sanitize_agent_name(name)
        # Store in-memory definition
        self.definitions[sanitized] = {
            "name": name,
            "system_prompt": system_prompt,
            "description": description
        }
        # Also persist as a static agent prompt template
        try:
            create_agent(sanitized, focus=description, mission=system_prompt, workspace=self.workspace)
        except Exception as e:
            logger.error(f"Failed to persist subagent template {sanitized}: {e}")
        return sanitized

    def _setup_workspace(self, mode: str, conversation_id: str) -> Path:
        if mode == "inherit":
            return self.workspace

        workspaces_dir = self.workspace / ".axon" / "workspaces"
        workspaces_dir.mkdir(parents=True, exist_ok=True)
        sub_workspace = workspaces_dir / conversation_id

        if mode == "branch":
            # Copy project files ignoring large runtime/build directories
            sub_workspace.mkdir(parents=True, exist_ok=True)
            ignore_patterns = shutil.ignore_patterns(
                ".git", "node_modules", ".next", ".venv", ".venv-build", "dist", "build", "release"
            )
            try:
                for item in os.listdir(self.workspace):
                    if item == ".axon":
                        continue
                    s = self.workspace / item
                    d = sub_workspace / item
                    if s.is_dir():
                        shutil.copytree(s, d, ignore=ignore_patterns, symlinks=True)
                    else:
                        shutil.copy2(s, d)
            except Exception as e:
                logger.error(f"Failed to copy workspace branch: {e}")
            return sub_workspace

        if mode == "share":
            # Try git worktree if git is available
            sub_workspace.mkdir(parents=True, exist_ok=True)
            git_dir = self.workspace / ".git"
            if git_dir.exists():
                try:
                    import subprocess
                    subprocess.run(
                        ["git", "worktree", "add", "-d", str(sub_workspace)],
                        cwd=str(self.workspace),
                        capture_output=True,
                        check=True
                    )
                    return sub_workspace
                except Exception as e:
                    logger.error(f"Git worktree failed, falling back to copy: {e}")

            # Fallback to copy/branch
            return self._setup_workspace("branch", conversation_id)

        return self.workspace

    def invoke_subagent(
        self,
        name: str,
        prompt: str,
        workspace_mode: str = "inherit",
        parent_llm: LLMManager | None = None
    ) -> str:
        conversation_id = f"sub-{uuid.uuid4().hex[:12]}"
        workspace_mode = workspace_mode.strip().lower()
        if workspace_mode not in ("inherit", "branch", "share"):
            workspace_mode = "inherit"

        sub_workspace = self._setup_workspace(workspace_mode, conversation_id)

        # Build subagent LLMManager
        from runtime_policy import load_runtime_policy

        policy = load_runtime_policy()
        api_key = parent_llm._api_key if parent_llm else None
        model = policy.subagent_model.strip() or (parent_llm.model if parent_llm else None)
        approve = parent_llm._approve if parent_llm else None

        sub_llm = LLMManager(
            api_key=api_key,
            model=model,
            approve=approve,
            workspace=sub_workspace
        )
        if parent_llm:
            sub_llm._base_url = parent_llm._base_url
            sub_llm._client = parent_llm._client
            sub_llm._on_tool = parent_llm._on_tool
            sub_llm._on_stream_token = parent_llm._on_stream_token
            sub_llm._on_stream_end = parent_llm._on_stream_end

        # Resolve system prompt
        system_prompt = ""
        sanitized = sanitize_agent_name(name)
        if sanitized in self.definitions:
            system_prompt = self.definitions[sanitized]["system_prompt"]
        else:
            loaded = load_agent_prompt(sanitized, self.workspace)
            if loaded:
                system_prompt = loaded

        if system_prompt:
            sub_llm.set_session_system_prompt(system_prompt)

        instance = SubagentInstance(
            conversation_id=conversation_id,
            name=name,
            prompt=prompt,
            workspace_mode=workspace_mode,
            workspace_path=sub_workspace,
            llm=sub_llm
        )

        self.instances[conversation_id] = instance

        # Run background loop task
        task = asyncio.create_task(self._run_subagent_loop(instance, prompt))
        instance.task = task

        return conversation_id

    async def _run_subagent_loop(self, instance: SubagentInstance, initial_prompt: str) -> None:
        try:
            # First message
            response = await instance.llm.send_message_async(initial_prompt)
            instance.status = "completed"
            
            # Broadcast the result back to parent/user
            import bridge
            await bridge.AxonBridge().broadcast({
                "type": "subagent_message",
                "conversation_id": instance.conversation_id,
                "sender": instance.name,
                "content": response.content or response.error or "Task completed"
            })

            # Keep listening to the inbox for further instructions
            while instance.status == "completed":
                msg = await instance.inbox.get()
                instance.status = "running"
                resp = await instance.llm.send_message_async(msg)
                instance.status = "completed"
                await bridge.AxonBridge().broadcast({
                    "type": "subagent_message",
                    "conversation_id": instance.conversation_id,
                    "sender": instance.name,
                    "content": resp.content or resp.error or "Processed message"
                })
        except asyncio.CancelledError:
            instance.status = "killed"
        except Exception as e:
            instance.status = "failed"
            logger.error(f"Error in subagent loop {instance.conversation_id}: {e}")

    async def send_message(self, recipient_id: str, message: str) -> bool:
        instance = self.instances.get(recipient_id)
        if not instance or instance.status not in ("completed", "running"):
            return False
        await instance.inbox.put(message)
        return True

    def list_subagents(self) -> list[dict[str, Any]]:
        return [
            {
                "conversation_id": inst.conversation_id,
                "name": inst.name,
                "status": inst.status,
                "workspace_mode": inst.workspace_mode,
                "workspace_path": str(inst.workspace_path),
            }
            for inst in self.instances.values()
        ]

    def kill_subagent(self, conversation_id: str) -> bool:
        instance = self.instances.get(conversation_id)
        if not instance:
            return False
        if instance.task and not instance.task.done():
            instance.task.cancel()
        instance.status = "killed"
        # Cleanup branched workspace if needed
        if instance.workspace_mode in ("branch", "share"):
            try:
                if instance.workspace_mode == "share":
                    import subprocess
                    subprocess.run(
                        ["git", "worktree", "prune"],
                        cwd=str(self.workspace),
                        capture_output=True
                    )
                shutil.rmtree(instance.workspace_path, ignore_errors=True)
            except Exception as e:
                logger.error(f"Failed to cleanup workspace: {e}")
        return True


# Global shared SubagentManager instance
subagent_manager = SubagentManager()
