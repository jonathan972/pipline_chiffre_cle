#!/usr/bin/env python3
from application import frozen_dependencies  # noqa: F401  (analyse PyInstaller)
from application.app import App

if __name__ == "__main__":
    App().mainloop()
