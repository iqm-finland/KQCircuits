#!/bin/bash

if [ -e singularity.pem ]; then
    echo "Building singularity image with encryption, needs sudo."
    sudo singularity build --pem-path singularity.pem kqclib singularity.def
else
    echo "Building singularity image."
    singularity build --fakeroot kqclib singularity.def
fi

mv kqclib libexec

echo "Singularity image is now built!"
echo "You can now run ./create_links.sh in order to get the executables for using the software in the image (instead of in your own system)"
