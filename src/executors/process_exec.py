"""
Process and system executor for running programs and managing processes.
"""
from __future__ import annotations

import subprocess
import os
import sys
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

    def start_program(self, program: str, args: List[str] | str | None = None, 
                     background: bool = True, process_id: str | None = None) -> Dict[str, Any]:
        """Start a program/application."""
        try:
            cmd = [program]
            if args:
                if isinstance(args, str):
                    args = [args]
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
        except FileNotFoundError as e:
            # Windows-specific fallbacks: find browser in common locations or use os.startfile/`start`
            if sys.platform.startswith("win"):
                url = args[0] if args and isinstance(args[0], str) and (args[0].startswith("http://") or args[0].startswith("https://")) else None
                # Try opening URL with default handler
                if url:
                    try:
                        os.startfile(url)  # type: ignore[attr-defined]
                        return {
                            "action": "process.start_program",
                            "success": True,
                            "program": "default_browser",
                            "background": True,
                            "method": "os.startfile",
                            "url": url
                        }
                    except Exception:
                        pass
                # Try common install paths for popular browsers
                candidates: List[str] = []
                pf = os.environ.get("ProgramFiles", r"C:\\Program Files")
                pf86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
                localapp = os.environ.get("LOCALAPPDATA", r"C:\\Users\\%USERNAME%\\AppData\\Local")
                mapping = {
                    "chrome.exe": [
                        os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
                        os.path.join(localapp, "Google", "Chrome", "Application", "chrome.exe"),
                    ],
                    "msedge.exe": [
                        os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
                        os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
                    ],
                    "firefox.exe": [
                        os.path.join(pf, "Mozilla Firefox", "firefox.exe"),
                        os.path.join(pf86, "Mozilla Firefox", "firefox.exe"),
                    ],
                }
                candidates.extend(mapping.get(program.lower(), []))
                for path in candidates:
                    if os.path.isfile(path):
                        try:
                            cmd2 = [path]
                            if args:
                                if isinstance(args, str):
                                    args = [args]
                                cmd2.extend(args)
                            process = subprocess.Popen(
                                cmd2,
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
                                "program": path,
                                "background": background,
                                "resolved_from": program
                            }
                        except Exception:
                            continue
                # Final fallback: use cmd `start` to let Windows resolve
                try:
                    # Build a command string: start "" program [args...]
                    quoted_args = " ".join([f'"{a}"' if " " in a else a for a in (args or [])])
                    cmdline = f'start "" {program} {quoted_args}'.strip()
                    subprocess.Popen(cmdline, shell=True)
                    return {
                        "action": "process.start_program",
                        "success": True,
                        "program": program,
                        "background": True,
                        "method": "cmd_start"
                    }
                except Exception:
                    pass
            # If all fallbacks fail, return the original error
            return {
                "action": "process.start_program",
                "success": False,
                "error": str(e),
                "program": program
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

    def monitor_process(self, process_name: str | None = None, pid: int | None = None, 
                       timeout: int = 60, alert_on_exit: bool = False) -> Dict[str, Any]:
        """Monitor a process for lifecycle events (start, exit, resource usage).
        
        Args:
            process_name: Name of process to monitor (e.g., "chrome.exe")
            pid: Process ID to monitor
            timeout: Duration to monitor in seconds
            alert_on_exit: Whether to trigger alert when process exits
            
        Returns:
            {
                "action": "process.monitor_process",
                "success": bool,
                "monitor_id": str,
                "process_info": {...},
                "events": [...]
            }
        """
        import time
        
        try:
            monitor_id = f"monitor_{process_name or pid}_{time.time()}"
            events = []
            start_time = time.time()
            process = None
            
            # Find the process
            if pid:
                try:
                    process = psutil.Process(pid)
                except psutil.NoSuchProcess:
                    return {
                        "action": "process.monitor_process",
                        "success": False,
                        "error": f"Process with PID {pid} not found"
                    }
            elif process_name:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if process_name.lower() in proc.info['name'].lower():
                            process = psutil.Process(proc.info['pid'])
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if not process:
                    return {
                        "action": "process.monitor_process",
                        "success": False,
                        "error": f"Process '{process_name}' not found"
                    }
            else:
                return {
                    "action": "process.monitor_process",
                    "success": False,
                    "error": "Either process_name or pid must be provided"
                }
            
            # Record initial state
            initial_info = {
                "name": process.name(),
                "pid": process.pid,
                "status": process.status(),
                "create_time": process.create_time(),
                "timestamp": time.time()
            }
            
            events.append({
                "type": "monitor_start",
                "timestamp": time.time(),
                "process_info": initial_info
            })
            
            # Monitor for timeout duration
            while time.time() - start_time < timeout:
                try:
                    # Check if process still exists
                    if process.is_running():
                        try:
                            cpu_percent = process.cpu_percent(interval=0.5)
                            memory_info = process.memory_info()
                            
                            events.append({
                                "type": "resource_sample",
                                "timestamp": time.time(),
                                "cpu_percent": cpu_percent,
                                "memory_mb": memory_info.rss / 1024 / 1024,
                                "process_status": process.status()
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    else:
                        # Process has exited
                        events.append({
                            "type": "process_exit",
                            "timestamp": time.time(),
                            "alert_triggered": alert_on_exit
                        })
                        break
                    
                    time.sleep(1)  # Sample every second
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process no longer accessible
                    events.append({
                        "type": "process_exit",
                        "timestamp": time.time(),
                        "alert_triggered": alert_on_exit
                    })
                    break
            
            return {
                "action": "process.monitor_process",
                "success": True,
                "monitor_id": monitor_id,
                "process_info": initial_info,
                "events": events,
                "elapsed": time.time() - start_time,
                "alert_on_exit": alert_on_exit
            }
            
        except Exception as e:
            return {
                "action": "process.monitor_process",
                "success": False,
                "error": str(e)
            }