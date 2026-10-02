#!/usr/env python3
import sys
import os
import importlib

def run_test(name, check_fn):
    print(f"Testing {name}...", end=" ")
    try:
        if check_fn():
            print("[\033[92mPASS\033[0m]")
            return True
        else:
            print("[\033[91mFAIL\033[0m]")
            return False
    except Exception as e:
        print(f"[\033[91mFAIL\033[0m] {e}")
        return False

def main():
    print("=== DroneAgent Self-Test ===")
    
    passed = 0
    total = 0
    
    tests = {
        "Python Version": lambda: sys.version_info >= (3, 8),
        "MAVSDK": lambda: importlib.import_module('mavsdk') is not None,
        "PySide6 (GUI)": lambda: importlib.import_module('PySide6') is not None,
        "YAML Configs": lambda: os.path.exists("config/base.yaml"),
        "Communication": lambda: importlib.import_module('communication') is not None,
        "Telemetry": lambda: importlib.import_module('telemetry') is not None,
        "Backend Interfaces": lambda: importlib.import_module('backend') is not None,
        "Decision Engine": lambda: importlib.import_module('decision') is not None,
        "Movement Controller": lambda: importlib.import_module('movement_controller') is not None,
    }
    
    for name, fn in tests.items():
        total += 1
        if run_test(name, fn):
            passed += 1
            
    print("===========================")
    print(f"Results: {passed}/{total} Passed")
    
    if passed == total:
        print("SYSTEM READINESS: \033[92mREADY FOR FLIGHT\033[0m")
        sys.exit(0)
    else:
        print("SYSTEM READINESS: \033[91mNOT READY\033[0m")
        sys.exit(1)

if __name__ == '__main__':
    main()
