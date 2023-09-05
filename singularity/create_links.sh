#!/bin/bash

function create_link () {
	ln -sfv "$PWD"/libexec/kqclib.sh bin/"$1"
}

EXECUTABLES=("ElmerSolver" "ElmerSolver_mpi" "ElmerGrid" "klayout" "kqclib" "paraview" "python")

echo "Creating symbolic links to the singularity image software"
mkdir -p bin
for EXECUTABLE in "${EXECUTABLES[@]}"
do
	create_link "$EXECUTABLE"
done

# move python away from bin such that it does not over-ride the system python if path is set to $PWD/bin
mv -v bin/python .

echo
echo "Among other executables, the image contains the following executables that are needed for the simulation workflow:"
echo "EXECUTABLES=(\"ElmerSolver\" \"ElmerSolver_mpi\" \"ElmerGrid\" \"klayout\" \"kqclib\" \"paraview\" \"python\")"
echo
echo "You could add your own executable in the list in ./create_links.sh (it is just a symbolic link named like the"
echo "executable that then needs to be found in the image)."
echo "Remember to add $PWD/bin to your PATH environment variable."
echo
echo "You can now prepare KQC simulations using the image:"
echo "For example go to ../klayout_package/python/scripts/simulations/" and run
echo
echo "'kqclib waveguides_sim_compare.py'"
echo
echo "or"
echo
echo "'$PWD/python waveguides_sim_compare.py'"
echo "(make sure python is run from $PWD)"
echo
echo "Note that python is not put in $PWD/bin such that it does not over-ride the system python even if the"
echo "folder is added to PATH environment variable."
echo
echo "In waveguides_sim_compare.py, one has to set"
echo
echo "workflow['python_executable']='kqclib'"
echo
echo "or"
echo
echo "workflow['python_executable']='$PWD/python'"
echo "(in order to use the singularity image or over-ride the system python with the latter executable, by moving it to $PWD/bin)."

echo
echo "The simulation scripts are then prepared in a subfolder (for example \$KQC_TMP_PATH/waveguides_sim_elmer in the affore mentioned example)."
echo "\$KQC_TMP_PATH folder is normally in ../tmp/, remember to set it! If you do not, you might get a read-only error when the singularity image tries to write to the image tmp folder that is *read-only*"
echo
echo "You will also likely need 'export DISPLAY=:0.0' to run GUI applications like KLayout or paraview"
echo
echo "In order to run the actual simulations:"
echo "Go to the folder and run ./simulation.sh"

