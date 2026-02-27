"""Legacy path shim.

Use the new authoritative server:

    python -m server_app
"""

from server_app.__main__ import main


if __name__ == "__main__":
    main()
