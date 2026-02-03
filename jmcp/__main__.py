import shutil
import sys
from jmcp.app import MCPApp


def main():
    print(f"DEBUG: ty path: {shutil.which('ty')}", file=sys.stderr)
    app = MCPApp()
    app.run()


if __name__ == "__main__":
    main()
