import sys
import os
import json
import urllib.parse
from pathlib import Path

# This script intercepts the MCP 'initialize' request from the IDE,
# extracts the workspace path (rootUri), changes the working directory to it,
# and then starts the graphify server.

class InterceptStdin:
    def __init__(self, original_stdin):
        self.original_stdin = original_stdin
        self.buffer = []
        
        while True:
            line = self.original_stdin.readline()
            if not line:
                break
            self.buffer.append(line)
            line_str = line.strip()
            if line_str:
                try:
                    msg = json.loads(line_str)
                    if msg.get("method") == "initialize":
                        root_uri = msg.get("params", {}).get("rootUri", "")
                        if root_uri.startswith("file://"):
                            # Parse the file URI to a local path
                            path = urllib.parse.unquote(root_uri[7:])
                            # Handle windows drive letters (e.g., /c:/foo -> c:/foo)
                            if path.startswith('/') and len(path) > 2 and path[2] == ':':
                                path = path[1:]
                            if os.path.exists(path):
                                os.chdir(path)
                        break
                except Exception:
                    pass

    def readline(self, *args, **kwargs):
        if self.buffer:
            return self.buffer.pop(0)
        return self.original_stdin.readline(*args, **kwargs)
        
    def read(self, *args, **kwargs):
        if self.buffer:
            res = "".join(self.buffer)
            self.buffer.clear()
            return res + self.original_stdin.read(*args, **kwargs)
        return self.original_stdin.read(*args, **kwargs)

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line
        
    def fileno(self):
        return self.original_stdin.fileno()

# Replace sys.stdin with our interceptor
sys.stdin = InterceptStdin(sys.stdin)

# Now start the actual graphify server
from graphify.serve import serve
if __name__ == "__main__":
    serve()
