#!/bin/bash

if [ -e singularity.pem ]; then
    echo "Building singularity image with encryption, needs sudo."
    echo "This can take up to 30 minutes."
    sudo singularity build --pem-path singularity.pem kqclib singularity.def
else
    echo "Building singularity image."
    echo "This can take up to 30 minutes. The output will be redirected into 'singularity_build.log'"
    if (( EUID == 0 )); then
        singularity build kqclib singularity.def &> "singularity_build.log"
    else
        singularity build --fakeroot kqclib singularity.def &> "singularity_build.log"
    fi
fi

if [ -e "kqclib" ]
then
    echo "Singularity image is now built!"
    mv kqclib libexec
    echo "You can now run ./create_links.sh in order to get the executables for using the software in the image (instead of in your own system)"
else
    echo "Error in building singularity image!"
    echo "Check end of 'singularity_build.log' for details"
fi
