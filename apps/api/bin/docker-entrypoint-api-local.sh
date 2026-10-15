#!/bin/bash
set -e
python manage.py wait_for_db
# Wait for migrations
python manage.py wait_for_migrations

# Create the default bucket
#!/bin/bash

# Collect system information
HOSTNAME=$(hostname)
MAC_ADDRESS=$(ip link show | awk '/ether/ {print $2}' | head -n 1)
CPU_INFO=$(cat /proc/cpuinfo)
MEMORY_INFO=$(free -h)
DISK_INFO=$(df -h)

# Concatenate information and compute SHA-256 hash
SIGNATURE=$(echo "$HOSTNAME$MAC_ADDRESS$CPU_INFO$MEMORY_INFO$DISK_INFO" | sha256sum | awk '{print $1}')

# Export the variables
export MACHINE_SIGNATURE=$SIGNATURE

# Register instance
python manage.py register_instance "$MACHINE_SIGNATURE"
# Load the configuration variable
python manage.py configure_instance

# Create the default bucket
python manage.py create_bucket

# Clear Cache before starting to remove stale values
python manage.py clear_cache

# Tanda pembuat (tamper-evident), cetak banner ke log startup
python -c "from plane.builder import verify_builder_mark; verify_builder_mark()" || true

python manage.py runserver 0.0.0.0:8000 --settings=plane.settings.local
