#!/usr/bin/env python
"""
Wrapper script to properly run the Dash app without Jupyter comm issues.
"""
import sys
import os

# Monkey-patch comm BEFORE importing dash
import sys
sys.modules['comm'] = None

# Also disable Jupyter completely
os.environ['DASH_DISABLE_JUPYTER'] = '1'

if __name__ == '__main__':
    from Main import Main
    main = Main()
    main.run()
