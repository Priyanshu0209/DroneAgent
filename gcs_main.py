#!/usr/bin/env python3
import argparse
from gcs_agent import GCSAgent

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DroneAgent Ground Control Station")
    parser.add_argument("-c", "--config", nargs="+", help="Path to config YAML files")
    args = parser.parse_args()
    
    configs = args.config if args.config else []
    if not any("base.yaml" in c for c in configs):
        configs.insert(0, "config/base.yaml")
        
    if not any("network_config.yaml" in c for c in configs):
        configs.insert(1, "config/network_config.yaml")
        
    agent = GCSAgent(configs)
    agent.start()
