import sys

print("ARGV DEBUG:", sys.argv)
from .cli import main

raise SystemExit(main())
