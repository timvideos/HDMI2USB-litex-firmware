#!/bin/bash

if [ -z "$PLATFORMS" ]; then
	if [ -z "$SKIP_PLATFORMS" ]; then
		SKIP_PLATFORMS="sim"
	fi
	if [ -z "$PLATFORM" ]; then
		PLATFORMS=$(ls targets/ | grep -v ".py" | grep -v "common" | grep -v "$SKIP_PLATFORMS" | sed -e"s+targets/++")
	else
		PLATFORMS="$PLATFORM"
	fi
fi
echo "Running with PLATFORMS='$PLATFORMS'"

source scripts/enter-env.sh || exit 1

ls -l $XILINX_DIR/opt/Xilinx/14.7/ISE_DS/ISE/bin/lin64/xreport
if [ -f $XILINX_DIR/opt/Xilinx/14.7/ISE_DS/ISE/bin/lin64/xreport ]; then
	HAVE_XILINX_ISE=1
else
	HAVE_XILINX_ISE=0
fi

set +x
set -e

function build() {
	export PLATFORM=$1
	export TARGET=$2
	export CPU=$3

	if [ -z "$PLATFORM" -o -z "$TARGET" -o -z "$CPU" ]; then
		echo "usage: build PLATFORM TARGET CPU"
		echo "  got: build '$PLATFORM' '$TARGET' '$CPU'"
		return 1
	fi

	# Create "clean" file list before build
	find | sort | grep -v "__pycache__" > /tmp/filelist.before

	export TARGET_BUILD_DIR=$PWD/build/${PLATFORM}_${TARGET}_${CPU}
	export LOGFILE=$TARGET_BUILD_DIR/output.$(date +%Y%m%d-%H%M%S).log
	echo "Using logfile $LOGFILE"

	echo ""
	echo ""
	echo ""
	echo "============================================="
	echo "- $PLATFORM $TARGET $CPU"
	echo "============================================="
	# Output the commands available to make it easier to debug.
	echo ""
	echo "- make help ($PLATFORM $TARGET $CPU)"
	echo "---------------------------------------------"
	make help
	echo "============================================="

	echo ""
	echo ""
	echo ""
	echo "- make test ($PLATFORM $TARGET $CPU)"
	echo "---------------------------------------------"
	make test || return 1
	echo "============================================="

	# We build the firmware first as it is very quick to build and
	# will let us find a whole classes of errors quickly.

	echo ""
	echo ""
	echo ""
	echo "- make firmware ($PLATFORM $TARGET $CPU) (prerun)"
	echo "---------------------------------------------"
	make -j4 firmware || return 1
	echo "- Firmware version data"
	echo "---------------------------------------------"
	VERSION_DATA="$(find $TARGET_BUILD_DIR -name version_data.c)"
	if [ -z "$VERSION_DATA" ]; then
		echo "No firmware version_data.c file found!"
	else
		cat $VERSION_DATA

		if grep -q -- "??" $VERSION_DATA; then
			echo "Repository had unknown files, failing to build!"
#			return 1
		fi

		if grep -q -- "-dirty" $VERSION_DATA; then
			echo "Repository was dirty, failing to build!"
#			return 1
		fi
	fi
	echo "============================================="

	# https://github.com/timvideos/HDMI2USB-misoc-firmware/issues/83
	# We have to clean after doing this otherwise if the gateware
	# has a dependency on the firmware that isn't correctly working
	# the travis build will still pass.
	echo ""
	echo ""
	echo ""
	echo "- make firmware-clean ($PLATFORM $TARGET $CPU) (prerun)"
	echo "---------------------------------------------"
	make firmware-clean
	echo "============================================="

	echo ""
	echo ""
	echo ""
	echo "- make gateware ($PLATFORM $TARGET $CPU)"
	echo "---------------------------------------------"
	if [ $HAVE_XILINX_ISE -eq 0 ]; then
		echo "Skipping gateware"
	else
		FILTER=$PWD/.travis/run-make-gateware-filter.py \
			make gateware || return 1
	fi
	echo "============================================="

	echo ""
	echo ""
	echo ""
	echo "- make firmware ($PLATFORM $TARGET $CPU)"
	echo "---------------------------------------------"
	make -j4 firmware || return 1
	echo "============================================="

	echo ""
	echo ""
	echo ""
	echo "- make image ($PLATFORM $TARGET $CPU)"
	echo "---------------------------------------------"
	make image || true
	echo "============================================="

	if [ ! -z "$PROGS" ]; then
		for PROG in $PROGS; do
			echo ""
			echo ""
			echo ""
			echo "- make load ($PROG $PLATFORM $TARGET $CPU)"
			echo "---------------------------------------------"
			# Allow the programming to fail.
			PROG=$PROG make load || true
		done
	fi

	# Save the resulting binaries into the prebuilt repo. The gateware
	# should always exist, but others might not.
	if [ ! -z "$PREBUILT_DIR" ]; then
		COPY_DEST="$PREBUILT_DIR/archive/$GIT_REVISION/$PLATFORM/$TARGET/$CPU/"
		echo ""
		echo ""
		echo ""
		echo "- Adding built files to github.com/$PREBUILT_REPO_OWNER/$PREBUILT_REPO"
		echo "---------------------------------------------"

		mkdir -p $COPY_DEST

		declare -a SAVE
		declare -a SAVE
		SAVE+="flash.bin" 				# Combined binary include gateware+bios+firmware
		# Gateware output for using
		SAVE+=("gateware/top.bit")			# Gateware in JTAG compatible format
		SAVE+=("gateware/top.bin")			# Gateware in flashable format
		# Gateware inputs for reference
		SAVE+=("gateware/top.v")			# Gateware verilog code
		SAVE+=("gateware/top.ucf")			# Gateware constraints
		# Gateware tools reporting information - Xilinx ISE
		SAVE+=("gateware/top_map.map")			# Report: Map
		SAVE+=("gateware/top.pad")			# Report: Pinout
		SAVE+=("gateware/top.par")			# Report: Place and route
		SAVE+=("gateware/top.srp")			# Report: Synthasis
		# Software support files
		SAVE+=("software/include/")			# Generated headers+config needed for QEmu, micropython, etc
		SAVE+=("software/bios/bios.*")			# BIOS for soft-cpu inside the gateware
		SAVE+=("software/firmware/firmware.*")		# HDMI2USB firmware for soft-cpu inside the gateware
		SAVE+=("support/fx2.hex")			# Firmware for Cypress FX2 on some boards

		for TO_SAVE in ${SAVE[@]}; do
			echo
			if ! ls $TARGET_BUILD_DIR/$TO_SAVE >/dev/null 2>&1; then
				echo "Nothing to save! ($TO_SAVE)"
				continue
			else
				echo "Saving $TO_SAVE"
			fi

			TO_SAVE_DIR="$(dirname $TO_SAVE)"
			mkdir -p $COPY_DEST/$TO_SAVE_DIR
			cp -v -r -a $TARGET_BUILD_DIR/$TO_SAVE $COPY_DEST/$TO_SAVE_DIR
		done

		# Logs, version information, etc
		mkdir -p $COPY_DEST/logs/
		cp $TARGET_BUILD_DIR/software/firmware/version_data.c $COPY_DEST/logs/version_data.c
		cp $TARGET_BUILD_DIR/output.*.log $COPY_DEST/logs/

		# Only hdmi2usb + lm32 is considered usable at the moment
		UNSTABLE_LINK="$PLATFORM/firmware/unstable"
		if [ "$TARGET" = "hdmi2usb" -a "$CPU" = "lm32" ]; then
			# Create link to latest unstable build
			rm $UNSTABLE_LINK
			ln -s ../../$COPY_DEST $UNSTABLE_LINK
			echo ""
			echo "- Added symlink of $UNSTABLE_LINK -> $COPY_DEST"
		fi
		(
		cd $COPY_DEST
		sha256sum $(find -type f) > sha256sum.txt
		cat sha256sum.txt
		)
		export GIT_AUTHOR_EMAIL="$ORIG_COMMITTER_EMAIL"
		export GIT_AUTHOR_NAME="$ORIG_COMMITTER_NAME"
		export GIT_COMMITTER_EMAIL="robot@timvideos.us"
		export GIT_COMMITTER_NAME="TimVideos Robot"
		echo ""
		(
		cd $PREBUILT_DIR
		git add -A .
		git commit -a \
			-m "Travis build #$TRAVIS_BUILD_NUMBER of $GIT_REVISION for PLATFORM=$PLATFORM TARGET=$TARGET CPU=$CPU" \
			-m "" \
			-m "From https://github.com/$TRAVIS_REPO_SLUG/tree/$TRAVIS_COMMIT" \
			-m "$TRAVIS_COMIT_MESSAGE"
		git diff HEAD~1 --stat=1000,1000
		)
		echo "============================================="
	fi

	if [ ! -z "$CLEAN_CHECK" ]; then
		echo ""
		echo ""
		echo ""
		echo "- make clean ($PLATFORM $TARGET)"
		echo "---------------------------------------------"
		make clean || return 1
		echo "============================================="

		# Check that make clean didn't leave anything behind
		find | sort | grep -v "__pycache__" > /tmp/filelist.after
		echo ""
		echo ""
		echo ""
		diff -u /tmp/filelist.before /tmp/filelist.after > /tmp/filelist.diff
		if [ $(wc -l < /tmp/filelist.diff) -eq 0 ] ; then
			echo "- make clean did not leave any generated files behind"
		else
			echo "- make clean left these files behind"
			echo "============================================="
			cat /tmp/filelist.diff
			echo "============================================="
			return 1
		fi
	fi
	return 0
}

declare -a SUCCESSES
declare -a FAILURES


# Clone prebuilt repo to copy results into
if [ -z "$GH_TOKEN" ]; then
	# Only if run by travis display error
	if [ ! -z $TRAVIS_BUILD_NUMBER  ]; then
		echo ""
		echo ""
		echo ""
		echo "- No Github token so unable to copy built files"
	fi
elif [ -z "$TRAVIS_BRANCH" ]; then
	echo ""
	echo ""
	echo ""
	echo "- No branch name, unable to copy built files"
else
	# Look at repo we are running in to determine where to try pushing to if in a fork
	PREBUILT_REPO=HDMI2USB-firmware-prebuilt
	PREBUILT_REPO_OWNER=$(echo $TRAVIS_REPO_SLUG|awk -F'/' '{print $1}')
	echo "PREBUILT_REPO_OWNER = $PREBUILT_REPO_OWNER"
	GIT_REVISION=$TRAVIS_BRANCH/$(git describe)
	ORIG_COMMITTER_NAME=$(git log -1 --pretty=%an)
	ORIG_COMMITTER_EMAIL=$(git log -1 --pretty=%ae)
	echo ""
	echo ""
	echo ""
	echo "- Uploading built files to github.com/$PREBUILT_REPO_OWNER/$PREBUILT_REPO"
	echo "---------------------------------------------"
	export PREBUILT_DIR="/tmp/HDMI2USB-firmware-prebuilt"
	git clone https://$GH_TOKEN@github.com/$PREBUILT_REPO_OWNER/${PREBUILT_REPO}.git $PREBUILT_DIR
	echo "============================================="
fi


for PLATFORM in $PLATFORMS; do
	if [ -z "$TARGETS" ]; then
		if [ -z "$SKIP_TARGETS" ]; then
			SKIP_TARGETS="__"
		fi
		if [ -z "$TARGET" -a -z "$TARGETS" ]; then
			TARGETS=$(ls targets/${PLATFORM}/*.py | grep -v "__" | grep -v "$SKIP_TARGETS" | sed -e"s+targets/${PLATFORM}/++" -e"s/.py//")
		else
			TARGETS="$TARGET"
		fi
	fi

	if [ -z "$CPUS" ]; then
		if [ -z "$CPU" ]; then
			#CPUS="lm32 or1k riscv32"
			CPUS="lm32"
		else
			CPUS="$CPU"
		fi
	fi
	echo ""
	echo ""
	echo ""
	echo "Running with TARGETS='$TARGETS'"
	for TARGET in $TARGETS; do
		for CPU in $CPUS; do
			build $PLATFORM $TARGET $CPU && :
			RETURN=$?
			if [ "$RETURN" -eq 0 ]; then
				SUCCESSES+=("$PLATFORM+$TARGET+$CPU")
			else
				FAILURES+=("$PLATFORM+$TARGET+$CPU")
			fi
		done
	done
done

if [ ! -z "$PREBUILT_DIR" ]; then
	echo ""
	echo ""
	echo ""
	echo "Pushing prebuilt binaries"
	echo "============================================="
	(
	cd $PREBUILT_DIR
	if [ "$TRAVIS_BRANCH" = "master" ]; then
		for PLATFORM in $PLATFORMS; do
			(
			cd $PLATFORM/firmware
			LATEST="$(ls ../../archive/master/ | tail -n 1)"
			HDMI2USB_FIRMWARE="$LATEST/$PLATFORM/hdmi2usb/lm32"
			if [ -d "$HDMI2USB_FIRMWARE" ]; then
				ln -sf unstable "$HDMI2USB_FIRMWARE"
				git add unstable
			fi
			)
		done
	fi
	git diff origin/master --stat=1000,1000
	while true; do
		git push --quiet origin master > /dev/null 2>&1 && break
		git fetch
		git merge origin/master -m "Merging #$TRAVIS_JOB_NUMBER of $GIT_REVISION"
	done
	)
fi

echo ""
echo ""
echo ""
echo "The following builds succeeded"
echo "============================================="

for S in ${SUCCESSES[@]}; do
	echo $S | sed -e's/+/ /g'
done
echo ""
echo ""
echo ""
echo "The following builds failed!"
echo "============================================="

for F in ${FAILURES[@]}; do
	echo $F | sed -e's/+/ /g'
done

echo ""
echo ""
echo ""
echo "============================================="

if [ ${#FAILURES[@]} -ne 0 ]; then
	echo "One or more builds failed :("
	exit 1
else
	echo "All builds succeeded! \\o/"
fi
