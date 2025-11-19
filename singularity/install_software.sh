#!/bin/bash

define_variables () {
    ####################
    # Config variables #
    ####################

    # Only applies to CentOS. Ubuntu uses the latest python
    export PYTHON_VERSION="3.10.11"

    export OPENSSL_VERSION="1.1.1t"
    # KLayout version
    # Target CPU architecture for compilation, see https://gcc.gnu.org/onlinedocs/gcc/x86-Options.html
    # Examples include `znver3` for AMD Zen 3, and `alderlake` for Intel 12th gen.
    #export MARCH="znver2"
    export MARCH="native"

    # Target MPI implementation: `openmpi` or `mpich`
    export TARGET_MPI="openmpi"
    export MPI_VERSION="4.1.4"

    # export TARGET_MPI="mpich"
    # export MPI_VERSION="4.0.2"
    export SLURM_MPI_TYPE=pmi2
    export PMIX_MCA_gds=hash
    export ELMER_HOME="/opt/elmer"
    export PATH=$ELMER_HOME/bin:$PATH
    export LD_LIBRARY_PATH=/usr/lib/:$ELMER_HOME/include:$ELMER_HOME/lib:/opt/elmer/share/elmersolver/lib:/opt/hypre/lib:/opt/scalapack/lib:/opt/mumps/lib:/opt/netcdf/lib:/opt/mmg/lib:/opt/parmmg/lib:/opt/nn/lib:/opt/csa/lib:$LD_LIBRARY_PATH
}

install_kqcircuits_package () {
    git clone https://github.com/iqm-finland/KQCircuits.git && cd KQCircuits || exit
    cd klayout_package/python || exit
    python -m pip install -r requirements/linux/requirements.txt
    python -m pip install --no-deps -e .
    python -m pip install -r requirements/linux/sim-requirements.txt
    ln -sf /usr/bin/python /usr/bin/kqclib
}

install_yum_packages () {
    # Upgrade packages to most recent versions
    yum -y upgrade

    # Enable EPEL (required by NVIDIA packages)
    yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

    # Install newer gcc
    yum -y install centos-release-scl
    yum -y install devtoolset-11
    yum -y install rh-git218
    yum -y remove cmake
    yum -y install cmake
    # shellcheck source=/dev/null
    source /opt/rh/devtoolset-11/enable
    # shellcheck source=/dev/null
    source /opt/rh/rh-git218/enable
    yum -y install libcurl

    # Install additional stuff
    yum -y install wget cmake lbzip2 libsndfile numactl zlib perl
}

install_deb_packages () {
    KL_FILE="klayout_0.30.1-1_amd64.deb"
    KL_HASH="11953ce5009a0e83f9840b506f80df49"

    apt update ; apt install -y apt-utils; apt upgrade -y
    DEBIAN_FRONTEND=noninteractive apt install -y tzdata
    apt install -y wget python-is-python3 python3-pip git libcurl4 libglu1-mesa libxft-dev
    apt install -y libopenblas-dev m4 libhdf5-dev gfortran build-essential cmake
    # These were needed by gmsh
    apt install -y libxcursor-dev libgl1 libglib2.0-0 libxinerama1
    wget -q https://www.klayout.org/downloads/Ubuntu-22/$KL_FILE
    echo "$KL_HASH  $KL_FILE" > klayout.md5
    md5sum --check klayout.md5 || exit
    apt install -y ./$KL_FILE
    apt clean -y
    rm -rf /var/lib/apt/lists/* ./klayout*

    # This is needed to use pip without venv
    python -m pip config set global.break-system-packages true
    python -m pip install --upgrade pip
    rm -rf /usr/lib/python3/dist-packages/klayout /usr/lib/python3/dist-packages/klayout.egg-info 
    install_kqcircuits_package

    # Installing paraview via apt causes secondary python with conflicting packages to be installed
    # apt install -y paraview
}

######################
# Elmer installation #
######################
# This section is based on an image provided by CSC

# Install mpich
compile_mpich () {

    wget -qO- "http://www.mpich.org/static/downloads/$MPI_VERSION/mpich-$MPI_VERSION.tar.gz" | tar xvz
    cd $MPI_VERSION || exit

    ./configure --enable-fast=all,O3 --prefix=/usr FFLAGS="-std=legacy" FCFLAGS="-std=legacy"

    make -j "$(nproc)"
    make install
    ldconfig
}

compile_openmpi () {
    MPI_VERSION_FOLDER="v${MPI_VERSION%.*}"
    MPI_TARBALL="openmpi-$MPI_VERSION.tar.gz"
    wget -qO- "https://download.open-mpi.org/release/open-mpi/$MPI_VERSION_FOLDER/$MPI_TARBALL" | tar xvz
    cd "openmpi-$MPI_VERSION" || exit

    ./configure --enable-fast=all,O3 --prefix=/usr FFLAGS="-std=legacy" FCFLAGS="-std=legacy"

    make -j "$(nproc)"
    make install
    ldconfig
    # For some reason, we don't get openmpi read correctly in scalapack build
    # So that is why we need the following hack
    ln -sf /usr/lib/openmpi /usr/lib/x86_64-linux-gnu/openmpi
    # ln -sf /usr/include/openmpi /usr/lib/x86_64-linux-gnu/openmpi/include
    ln -sf /usr/include/ /usr/lib/x86_64-linux-gnu/openmpi/include
    #ln -sf /usr/include /usr/lib/x86_64-linux-gnu/openmpi/include
    # additionally needed libraries
}

compile_mpi () {
    if [[ -z ${TARGET_MPI} ]]; then
        echo "TARGET_MPI environment variable is not found! Choosing 'openmpi'."
        TARGET_MPI='openmpi'
    fi

    if [[ "${TARGET_MPI}" = "mpich" ]]; then
        echo "TARGET_MPI environment variable is set to 'mpich'. If you need a specific version, you need to modify install_software.sh:compile_mpich()"
        compile_mpich
    elif [[ "${TARGET_MPI}" = "openmpi" ]]; then
        echo "TARGET_MPI environment variable is set to 'openmpi'. If you need a specific version, you need to modify install_software.sh:compile_openmpi()"
        compile_openmpi
    else
        echo "TARGET_MPI environment variable is neither 'mpich' nor 'openmpi'! Choosing 'openmpi'."
        compile_openmpi
    fi
}

compile_netcdf () {
    git clone --depth 1 --branch v4.6.3 https://github.com/Unidata/netcdf-c.git
    cd netcdf-c || exit
    mkdir build
    cd build/ || exit
    cmake -DCMAKE_INSTALL_PREFIX=/opt/netcdf  -DCMAKE_C_FLAGS="-O3 -fopenmp -funroll-loops" -DENABLE_HDF5:BOOL=FALSE ..
    make -j "$(nproc)"
    make install
    export LD_LIBRARY_PATH="/opt/netcdf/lib:$LD_LIBRARY_PATH"
    cd /opt/src || exit
    git clone --depth 1 --branch v4.5.2 https://github.com/Unidata/netcdf-fortran
    cd netcdf-fortran/ || exit
    mkdir build
    cd build/ || exit
    cmake -DCMAKE_INSTALL_PREFIX=/opt/netcdf -DENABLE_HDF5:BOOL=FALSE -DUSE_HDF5:BOOL=FALSE \
          -DCMAKE_Fortran_FLAGS="-std=legacy -O3 -fopenmp -funroll-loops" -DCMAKE_C_FLAGS="-O3 -fopenmp -funroll-loops"  ..
    make -j "$(nproc)"
    make install
    cd /opt/src || exit
    #rm -rf netcdf-c netcdf-fortran
}

compile_hypre () {
    git clone https://github.com/hypre-space/hypre.git
    cd /opt/src/hypre/src || exit
    # Freeze Hypre version to a commit from 3.6.2025
    git checkout 1d841da1801c66691f72e3e914768ff32bcd3772
    ./configure --with-openmp --with-blas --with-lapack --prefix="/opt/hypre"  CC="mpicc -fPIC -O3 -march=$MARCH"
    make -j "$(nproc)"
    make install
    cd /opt/src || exit
    #rm -rf hypre
    export LD_LIBRARY_PATH="/opt/hypre/lib:$LD_LIBRARY_PATH"
}

# compile/install BLACS/Scalapack (needed by MUMPS)
compile_scalapack () {
    git clone https://github.com/Reference-ScaLAPACK/scalapack.git
    cd scalapack || exit
    mkdir build
    cd build || exit
    cmake -DCMAKE_INSTALL_PREFIX=/opt/scalapack  -DBUILD_SHARED_LIBS=ON -DCMAKE_C_FLAGS="-O3 -fopenmp -funroll-loops" \
          -DCMAKE_Fortran_FLAGS="-O3 -fPIC -funroll-loops" ..
    make -j "$(nproc)" install
    cd /opt/src || exit
    #rm -rf scalapack
    export LD_LIBRARY_PATH="/opt/scalapack/lib:$LD_LIBRARY_PATH"
}

# compile/install MUMPS
compile_MUMPS () {
    wget -qO- https://zenodo.org/record/7888117/files/MUMPS_5.6.0.tar.gz?download=1 | tar xvz
    cd MUMPS_5.6.0 || exit
    cp /opt/Makefile.inc ./
    # this hack is needed because include directory is again wrongly set up
    ln -sf /usr/include /include
    make -j "$(nproc)"
    mkdir /opt/mumps
    mv lib /opt/mumps
    mv include /opt/mumps
    cd ..
    #rm -rf MUMPS_5.6.0
    export LD_LIBRARY_PATH="/opt/mumps/lib:$LD_LIBRARY_PATH"
}

# compile/install MMG
compile_mmg () {
    cd /opt/src || exit
    git clone https://github.com/MmgTools/mmg.git
    cd mmg || exit
    git checkout develop
    # Use version from 12/2024. Recent versions cause Elmer compilation to fail.
    git checkout e4fe5516a6f6dc49f59d6d35b4ce8fbaba2bfea3
    mkdir build
    cd build || exit
    cmake -DCMAKE_INSTALL_PREFIX="/opt/mmg" -D CMAKE_BUILD_TYPE=RelWithDebInfo -D BUILD_SHARED_LIBS:BOOL=TRUE \
          -D MMG_INSTALL_PRIVATE_HEADERS=ON -D CMAKE_C_FLAGS="-fPIC  -g" -D CMAKE_CXX_FLAGS="-fPIC -std=c++11 -g"  ..
    make -j "$(nproc)" install
}

# compile/install PARMMG
compile_parmmg () {
    cd /opt/src || exit
    git clone https://github.com/MmgTools/ParMmg.git
    cd ParMmg || exit
    # commit f981ff8eba8a45131821893440720556394e2cad
    git checkout develop
    mkdir build
    cd build || exit
    cmake -D CMAKE_INSTALL_PREFIX="/opt/parmmg" -D CMAKE_BUILD_TYPE=RelWithDebInfo -D USE_VTK:BOOL=FALSE \
          -D BUILD_SHARED_LIBS:BOOL=TRUE -D DOWNLOAD_MMG=OFF  -D MMG_DIR="/opt/mmg"  -D MMG_DIR_FOUND="/opt/mmg" \
          -D MMG_libmmgtypes.h_DIRS="/opt/mmg/include/mmg/common" -D MMG_mmg_LIBRARY="/opt/mmg/lib/libmmg.so"  ..
    make -j "$(nproc)" install
    export LD_LIBRARY_PATH="/opt/mmg/lib:/opt/parmmg/lib:$LD_LIBRARY_PATH"
    cd /opt/src || exit
    #rm -rf mmg/ ParMmg/
}

# NN (for ScatteredDataInterpolator)
compile_NN() {
    git clone https://github.com/sakov/nn-c.git
    cd nn-c/nn || exit
    export CFLAGS="-fPIC -O3 -march=$MARCH -ffast-math -funroll-loops"
    ./configure --prefix="/opt/nn"
    make clean
    gcc -c -DTRILIBRARY -fPIC -O2 -w -ffloat-store -I. triangle.c
    make -j "$(nproc)" install
    cd /opt/src || exit
    #rm -rf nn-c
}

# csa
compile_csa () {
    git clone https://github.com/sakov/csa-c.git
    cd csa-c/csa || exit
    ./configure --prefix="/opt/csa"
    make -j "$(nproc)" install
    cd /opt/src || exit
    #rm -rf csa-c
    export LD_LIBRARY_PATH="/opt/nn/lib:/opt/csa/lib:$LD_LIBRARY_PATH"
}

# and, finally, Elmer
# Note currently compiling Elmer without Hypre, ElmerIce and ParMMG
compile_elmer () {
    local REMOVE_SOURCE=$1
    git clone https://github.com/ElmerCSC/elmerfem.git
    cd elmerfem || exit
    git checkout devel
    git submodule update --init
    mkdir build
    cd build || exit
    cmake ../ -DCMAKE_INSTALL_PREFIX=/opt/elmer \
            -DWITH_MPI:BOOL=TRUE \
            -DWITH_LUA:BOOL=TRUE \
            -DWITH_OpenMP:BOOL=TRUE \
            -DWITH_ElmerIce:BOOL=FALSE \
            -DWITH_NETCDF:BOOL=TRUE \
            -DWITH_GridDataReader:BOOL=TRUE \
            -DNETCDF_INCLUDE_DIR="/opt/netcdf/include" \
            -DNETCDF_LIBRARY="/opt/netcdf/lib/libnetcdf.so" \
            -DNETCDFF_LIBRARY="/opt/netcdf/lib/libnetcdff.so" \
            -DWITH_Zoltan:BOOL=TRUE \
            -DWITH_Mumps:BOOL=TRUE \
            -DMUMPS_ROOT="/opt/mumps" \
            -DSCALAPACK_LIBRARIES="-L/opt/scalapack/lib -lscalapack" \
            -DWITH_Hypre:BOOL=TRUE \
            -DHYPRE_ROOT="/opt/hypre" \
            -DWITH_ScatteredDataInterpolator:BOOL=TRUE \
            -DCSA_LIBRARY="/opt/csa/lib/libcsa.a" \
            -DCSA_INCLUDE_DIR="/opt/csa/include" \
            -DNN_INCLUDE_DIR="/opt/nn/include" \
            -DNN_LIBRARY="/opt/nn/lib/libnn.a" \
            -DWITH_MMG:BOOL=TRUE \
            -DMMG_ROOT="/opt/mmg" \
            -DMMG_LIBRARY="/opt/mmg/lib/libmmg.so" \
            -DMMG_INCLUDE_DIR="/opt/mmg/include" \
            -DWITH_PARMMG:BOOL=FALSE \
            -DPARMMGROOT="/opt/parmmg" \
            -DCMAKE_C_FLAGS="-O3 -fopenmp -funroll-loops -march=$MARCH" \
            -DCMAKE_Fortran_FLAGS="-O3 -fPIC -funroll-loops -march=$MARCH"

    make -j "$(nproc)" install || exit
    cd /opt/src || exit
    if $REMOVE_SOURCE
    then
        rm -rf elmerfem
    fi
}

install_kqcircuits_and_deps_centos () {
    ###########################
    # KQCircuits installation #
    ###########################

    KL_FILE="klayout-0.30.1-0.x86_64.rpm"
    KL_HASH="368143dfdbfe5119f915fbf6d1efa067"

    yum -y install -y xorg-x11-server-Xvfb mesa-libGL libXft-devel
    yum -y install -y paraview

    wget -q "https://www.klayout.org/downloads/CentOS_7/$KL_FILE"
    echo "$KL_HASH  $KL_FILE" > klayout.md5
    md5sum --check klayout.md5
    yum install -y "./$KL_FILE"
    rm $KL_FILE klayout.md5

    # Get gmsh (and its deps.), see https://gitlab.onelab.info/gmsh/gmsh/-/wikis/Gmsh-compilation
    wget -qO- http://download.savannah.gnu.org/releases/freetype/freetype-2.12.1.tar.gz | tar xvz
    cd freetype-2.12.1 || exit
    ./configure
    make -j "$(nproc)" install
    cd /opt/src || exit

    wget -qO- "http://git.dev.opencascade.org/gitweb/?p=occt.git;a=snapshot;h=refs/tags/V7_7_1;sf=tgz" | tar xvz
    cd occt-V7_7_1 || exit
    mkdir build
    cd build || exit
    cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_MODULE_Draw=0 -DBUILD_MODULE_Visualization=0 -DBUILD_MODULE_ApplicationFramework=0 ..
    make -j "$(nproc)" install
    cd /opt/src || exit

    git clone -b release-1.3.8 https://github.com/fltk/fltk.git
    cd fltk || exit
    mkdir build
    cd build || exit
    cmake -DCMAKE_POSITION_INDEPENDENT_CODE=ON ..
    make -j "$(nproc)" install
    cd /opt/src || exit

    git clone -b gmsh_4_11_1 http://gitlab.onelab.info/gmsh/gmsh.git
    cd gmsh || exit
    mkdir build
    cd build || exit
    cmake -DENABLE_BUILD_DYNAMIC=1 -DCMAKE_CXX_FLAGS="-O3 -march=$MARCH" ..
    make -j "$(nproc)" && make install
    mkdir ../lib
    ln -s "$(pwd)/libgmsh.so.4.11.1" "$(pwd)/libgmsh.so.4.11" "$(pwd)/libgmsh.so" "$(pwd)/../lib"
    ln -s "$(pwd)/libgmsh.so.4.11.1" "$(pwd)/libgmsh.so.4.11" "$(pwd)/libgmsh.so" "/usr/local/lib"
    cd ../api || exit
    if [[ -z ${PYTHONPATH} ]]; then
        PYTHONPATH="$(pwd)"
        export PYTHONPATH
    else
        PYTHONPATH="${PYTHONPATH}:$(pwd)"
    fi
    # retain PYTHONPATH when running container
    export SINGULARITYENV_PYTHONPATH=${PYTHONPATH}
    cd /opt/src || exit

    # Get recent OpenSSL (required for pip)
    yum -y install openssl-devel bzip2-devel libffi-devel
    yum -y groupinstall "Development Tools"
    yum -y install perl-IPC-Cmd perl-Test-Simple
    wget -qO- "https://www.openssl.org/source/openssl-$OPENSSL_VERSION.tar.gz" | tar xvz
    cd "openssl-$OPENSSL_VERSION" || exit
    ./config --prefix=/usr --openssldir=/etc/ssl --libdir=lib no-shared zlib-dynamic
    make -j "$(nproc)" && make test && make install
    cd .. || exit

    # Update Python
    yum clean all  # need to clean before installing Python 3, as system Python 2 breaks
    wget -qO- "https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz" | tar xvz
    cd "Python-$PYTHON_VERSION" || exit
    export CFLAGS="-march=$MARCH -O3 -pipe"
    ./configure --enable-optimizations --with-openssl=/usr
    make -j "$(nproc)" altinstall
    cd .. || exit
    rm -rf Python-"$PYTHON_VERSION"
    # Convert e.g. 3.10.2 => 3.10
    PYTHON_BIN_VERSION=$(echo "$PYTHON_VERSION" | awk -F'.' '{print $1"."$2}')
    alternatives --install /usr/bin/python python "/usr/local/bin/python$PYTHON_BIN_VERSION" 1
    alternatives --set python "/usr/local/bin/python$PYTHON_BIN_VERSION"

    # TODO switch to using pinned requirements by using install_kqcircuits_package()
    python -m pip install --upgrade pip
    rm -rf /usr/lib/python3/dist-packages/klayout /usr/lib/python3/dist-packages/klayout.egg-info
    git clone https://github.com/iqm-finland/KQCircuits.git && cd KQCircuits || exit
    python -m pip install -e klayout_package/python
    python -m pip install pandas
    ln -s /usr/bin/python /usr/bin/kqclib

    # set version as label, works for Singularity versions >= 3.7
    # KQC_VERSION="$(python -m pip show kqcircuits | grep -oP 'Version: \K.*')"
    # echo "org.opencontainers.image.version $KQC_VERSION" >> "$SINGULARITY_LABELS"

    # KQCircuits require gmsh
    pip install gmsh
}

define_variables
#install_yum_packages # Centos
install_deb_packages
compile_mpi

# compiling libraries at /opt/src
mkdir  /opt/src
cd /opt/src || exit

compile_netcdf
compile_hypre
compile_scalapack
compile_MUMPS
compile_mmg
#compile_parmmg
compile_NN
compile_csa
compile_elmer true

#install_kqcircuits_and_deps_centos
