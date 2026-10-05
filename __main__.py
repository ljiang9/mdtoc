"""Enables `python -m mdtoc`."""
import sys

if __package__:
    from .mdtoc import main
else:  # 直接运行 __main__.py 的兜底
    from mdtoc import main

if __name__ == "__main__":
    sys.exit(main())
