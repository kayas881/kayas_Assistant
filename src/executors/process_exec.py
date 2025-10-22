"""
Process and system executor for running programs and managing processes.
"""
from __future__ import annotations

import subprocess
import psutil
import signal
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class ProcessConfig:
    shell: bool = True
    timeout: int = 30
    capture_output: bool = True
    working_dir: Optional[Path] = None


class ProcessExecutor:
    def __init__(self, cfg: ProcessConfig | None = None):
        self.cfg = cfg or ProcessConfig()
        self.active_processes: Dict[str, subprocess.Popen] = {}

    def run_command(self, command: str, timeout: int | None = None, shell: bool | None = None, 
                   working_dir: str | None = None) -> Dict[str, Any]:
        """Run a shell command and return the output."""
        try:
            result = subprocess.run(
                command,
                shell=shell if shell is not None else self.cfg.shell,
                capture_output=self.cfg.capture_output,
                text=True,
                timeout=timeout or self.cfg.timeout,
                cwd=working_dir or self.cfg.working_dir
            )
            
            return {
                "action": "process.run_command",
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }
        except subprocess.TimeoutExpired as e:
            return {
                "action": "process.run_command",
                "success": False,
                "error": f"Command timed out after {timeout or self.cfg.timeout} seconds",
                "command": command
            }
        except Exception as e:
            return {
                "action": "process.run_command",
                "success": False,
                "error": str(e),
                "command": command
            }

    def start_program(self, program: str, args: List[str] | None = None, 
                     background: bool = True, process_id: str | None = None) -> Dict[str, Any]:
        """Start a program/application."""
        try:
            cmd = [program]
            if args:
                cmd.extend(args)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if background else None,
                stderr=subprocess.PIPE if background else None,
                text=True
            )
            
            pid_key = process_id or f"proc_{process.pid}"
            if background:
                self.active_processes[pid_key] = process
            
            return {
                "action": "process.start_program",
                "success": True,
                "pid": process.pid,
                "process_id": pid_key,
                "program": program,
                "background": background
            }
        except Exception as e:
            return {
                "action": "process.start_program",
                "success": False,
                "error": str(e),
                "program": program
            }

    def kill_process(self, process_id: str | None = None, pid: int | None = None, 
                    name: str | None = None) -> Dict[str, Any]:
        """Kill a process by ID, PID, or name."""
        try:
            killed = []
            
            # Kill by tracked process_id
            if process_id and process_id in self.active_processes:
                proc = self.active_processes[process_id]
                proc.terminate()
                proc.wait(timeout=5)
                killed.append(process_id)
                del self.active_processes[process_id]
            
            # Kill by PID
            elif pid:
                process = psutil.Process(pid)
                process.terminate()
                process.wait(timeout=5)
                killed.append(pid)
            
            # Kill by name
            elif name:
                for proc in psutil.process_iter(['pid', 'name']):
                    if name.lower() in proc.info['name'].lower():
                        proc.terminate()
                        killed.append(proc.info['pid'])
            
            return {
                "action": "process.kill",
                "success": len(killed) > 0,
                "killed": killed
            }
        except Exception as e:
            return {
                "action": "process.kill",
                "success": False,
                "error": str(e)
            }

    def list_processes(self, filter_name: str | None = None) -> Dict[str, Any]:
        """List running processes."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    info = proc.info
                    if filter_name and filter_name.lower() not in info['name'].lower():
                        continue
                    
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu_percent": info.get('cpu_percent', 0),
                        "memory_mb": info.get('memory_info', {}).rss / 1024 / 1024 if info.get('memory_info') else 0
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "action": "process.list",
                "success": True,
                "count": len(processes),
                "processes": processes[:50]  # Limit to 50 for sanity
            }
        except Exception as e:
            return {
                "action": "process.list",
                "success": False,
                "error": str(e)
            }

    def get_system_info(self) -> Dict[str, Any]:
        """Get system resource information."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "action": "process.system_info",
                "success": True,
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": memory.total / 1024 / 1024 / 1024,
                    "available_gb": memory.available / 1024 / 1024 / 1024,
                    "used_gb": memory.used / 1024 / 1024 / 1024,
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / 1024 / 1024 / 1024,
                    "used_gb": disk.used / 1024 / 1024 / 1024,
                    "free_gb": disk.free / 1024 / 1024 / 1024,
                    "percent": disk.percent
                }
            }
        except Exception as e:
            return {
                "action": "process.system_info",
                "success": False,
                "error": str(e)
            }