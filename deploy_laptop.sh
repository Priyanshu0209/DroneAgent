#!/bin/bash
# Deploy Ground Control Station (Laptop)

DEPLOY_DIR="deploy_laptop"
mkdir -p $DEPLOY_DIR

echo "Copying GCS files..."
cp -r gui $DEPLOY_DIR/
cp -r config $DEPLOY_DIR/
cp gcs_main.py $DEPLOY_DIR/
cp gcs_agent.py $DEPLOY_DIR/
cp communication.py $DEPLOY_DIR/
cp packet.py $DEPLOY_DIR/
cp logger.py $DEPLOY_DIR/
cp config.py $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/

echo "Creating start script..."
cat << 'EOF' > $DEPLOY_DIR/start_gcs.sh
#!/bin/bash
python3 gcs_main.py "$@"
EOF
chmod +x $DEPLOY_DIR/start_gcs.sh

echo "GCS deployment tree created in $DEPLOY_DIR"
