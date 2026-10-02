import logging
from backend import HardwareInterface
from simulation_backend import SimulationBackend
from real_backend import RealDroneBackend

def BackendFactory(config: dict, logger: logging.Logger) -> HardwareInterface:
    """
    Instantiates and returns the appropriate HardwareInterface backend
    based on the configuration.
    
    Args:
        config: Configuration dictionary.
        logger: Logger instance.
        
    Returns:
        HardwareInterface implementation (SimulationBackend or RealDroneBackend).
    """
    mode = config.get("mode", "simulation").lower()
    
    if mode == "simulation":
        logger.info("BackendFactory: Creating SimulationBackend")
        return SimulationBackend(config, logger)
    elif mode == "real":
        logger.info("BackendFactory: Creating RealDroneBackend")
        return RealDroneBackend(config, logger)
    else:
        logger.error(f"BackendFactory: Unknown mode '{mode}', defaulting to SimulationBackend")
        return SimulationBackend(config, logger)
