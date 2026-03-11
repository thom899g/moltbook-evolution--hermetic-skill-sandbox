"""
Moltbook Stage Decorator - Core API for Hermetic Skill Sandbox
Implements the 3-line API for skill developers with strict isolation
"""
import os
import sys
import json
import inspect
import logging
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, cast
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
from functools import wraps
import tempfile
import threading

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])

class CapabilityType(Enum):
    """Types of capabilities a skill can request"""
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    COMPUTE = "compute"
    ENVIRONMENT = "environment"

@dataclass
class NetworkCapability:
    """Network access capability specification"""
    host: str
    port: int
    protocol: str = "tcp"
    direction: str = "outbound"
    
    def validate(self) -> bool:
        """Validate network capability parameters"""
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Invalid port: {self.port}")
        if self.protocol not in ["tcp", "udp"]:
            raise ValueError(f"Invalid protocol: {self.protocol}")
        if self.direction not in ["inbound", "outbound"]:
            raise ValueError(f"Invalid direction: {self.direction}")
        return True
    
    def to_string(self) -> str:
        """Convert to capability string format"""
        return f"net:{self.host}:{self.port}:{self.protocol}:{self.direction}"

@dataclass
class FilesystemCapability:
    """Filesystem access capability specification"""
    path: str
    mode: str  # "ro", "rw", "wo"
    
    def validate(self) -> bool:
        """Validate filesystem capability parameters"""
        if self.mode not in ["ro", "rw", "wo"]:
            raise ValueError(f"Invalid mode: {self.mode}")
        
        # Prevent path traversal attempts
        abs_path = os.path.abspath(self.path)
        if '..' in self.path or self.path.startswith('/'):
            # Only allow specific mounted paths, not arbitrary system paths
            raise ValueError(f"Potentially unsafe path: {self.path}")
        
        return True
    
    def to_string(self) -> str:
        """Convert to capability string format"""
        return f"fs:{self.m