#!/bin/bash

if [ "`whoami`" = "root" ]
then
    echo "Running the script as root is not permitted"
    exit 1
fi

set -e

SETUP_SRC=$(realpath ${BASH_SOURCE[@]})
SETUP_DIR=$(dirname $SETUP_SRC)
TOP_DIR=$(realpath $SETUP_DIR/..)
BUILD_DIR=$TOP_DIR/build

if [ ! -e $BUILD_DIR ]; then
 echo "You need to build the firmware first.  Please see README.md"
 exit 1
fi

source $TOP_DIR/scripts/setup-env.sh

(
	cd $TOP_DIR
	echo ""
	echo "IF THIS FAILS:"
	echo " * Ensure USB plugged into PROG port for programming"
	echo " * Ensure USB also plugged into UART port for HDMI2USB capture"
	echo " * If using a VM, ensure devices are passed through (will change during flash)"
	echo " * Has HDMI2USB already been flashed since last power cycle?"
	echo ""
        sleep 2

	echo "Attempting to load gateware.."

	make load-gateware; sleep 2

	echo "Attempting to load firmware..."
	make load-fx2; sleep 1

	echo "Connecting to firmware.  Type 'help' for commands..."
	make connect-softcpu

	echo "Opening video output..."
	make view
)
