
MONITOR_SCRIPT = """#!/bin/bash
    MONITOR_LOCATION="https://raw.github.com/falkrust/PloneMonitor/master/monitor.py"
    MONITOR_FNAME="monitor.py"

    function monitor_setup {
        # $1 is plone location
        # $2 is authToken
        cd ~
        echo changed directory to $PWD
        echo "downloading monitor script"
        wget -N $MONITOR_LOCATION

        if [ -f $MONITOR_FNAME ]; then
        echo "file downloaded successfully"
        echo "setting exec permissions"
        chmod +x $MONITOR_FNAME

        echo "Calling the monitor script now"
        python2 $MONITOR_FNAME $1 $2
        fi
    }

"""

TEST_MACHINE_SCRIPT = """#!/bin/bash
	function request_and_shutdown {
	echo "Making a request to"
	echo $1
	wget $1
	echo "Request complete"
	echo "Shutting down the machine now"
	shutdown -h now
	}

	request_and_shutdown $1
"""