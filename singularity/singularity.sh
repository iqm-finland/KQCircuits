#!/bin/bash

USE_SUDO="true"
{ echo "Building singularity image with fakeroot..." && singularity build --fakeroot kqclib singularity.def && USE_SUDO="false"; } || \
	{ echo "Fakeroot build failed, let's try using sudo" && sudo singularity build kqclib singularity.def; } && \
	mv kqclib libexec && mkdir -p bin && ln -s ../libexec/kqclib.sh bin/kqclib || exit

if [[ "${USE_SUDO}" == "true" ]]; then
	sudo chown -R "$USER":"$USER" bin
fi
chmod 755 libexec/kqclib.sh

echo "Singularity image is now built!"
echo "You can now run ./create_links.sh in order to get the executables for using the software in the image (instead of in your own system)"
