#!/bin/bash
# Deploy DroneNode (Raspberry Pi)

DEPLOY_DIR="deploy_drone"
mkdir -p $DEPLOY_DIR

echo "Copying Drone files..."
cp -r config $DEPLOY_DIR/
cp drone_main.py $DEPLOY_DIR/
cp backend*.py $DEPLOY_DIR/
cp real_backend.py $DEPLOY_DIR/
cp simulation_backend.py $DEPLOY_DIR/
cp communication.py $DEPLOY_DIR/
cp packet.py $DEPLOY_DIR/
cp decision.py $DEPLOY_DIR/
cp formation.py $DEPLOY_DIR/
cp heartbeat.py $DEPLOY_DIR/
cp mission.py $DEPLOY_DIR/
cp movement_controller.py $DEPLOY_DIR/
cp neighbor.py $DEPLOY_DIR/
cp planner.py $DEPLOY_DIR/
cp state_machine.py $DEPLOY_DIR/
cp telemetry.py $DEPLOY_DIR/
cp collision.py $DEPLOY_DIR/
cp logger.py $DEPLOY_DIR/
cp config.py $DEPLOY_DIR/
cp utils.py $DEPLOY_DIR/

cp droneagent.service $DEPLOY_DIR/
cp setup_systemd.sh $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/

echo "Creating start script..."
cat << 'EOF' > $DEPLOY_DIR/start_drone.sh
#!/bin/bash
python3 drone_main.py "$@"
EOF
chmod +x $DEPLOY_DIR/start_drone.sh

echo "Drone deployment tree created in $DEPLOY_DIR"
