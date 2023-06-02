# This file is used for compiling MUMPS within the provided singularity image

# Begin orderings
LPORDDIR = $(topdir)/PORD/lib/
IPORD    = -I$(topdir)/PORD/include/
LPORD    = -L$(LPORDDIR) -lpord

ORDERINGSF =  -Dpord
ORDERINGSC  = $(ORDERINGSF)

LORDERINGS = $(LMETIS) $(LPORD) $(LSCOTCH)
IORDERINGSF = $(ISCOTCH)
IORDERINGSC = $(IMETIS) $(IPORD) $(ISCOTCH)
# End orderings
################################################################################

PLAT    =
LIBEXT  = .a
OUTC    = -o 
OUTF    = -o 
RM = /bin/rm -f
CC = mpicc
FC = mpif90
FL = mpif90
AR = ar vr 
RANLIB = ranlib
LAPACK = -lopenblas
SCALAP  = -L /opt/scalapack/lib -lscalapack 

INCPAR = -I$(OMPI_DIR)/include

LIBPAR = $(SCALAP) $(LAPACK)  -lmpi 

INCSEQ = -I$(topdir)/libseq
LIBSEQ  = $(LAPACK) -L$(topdir)/libseq -lmpiseq

LIBBLAS = -lopenblas
LIBOTHERS = -lpthread

# Preprocessor defs for calling Fortran from C (-DAdd_ or -DAdd__ or -DUPPER)
CDEFS   = -DAdd_

# Begin Optimized options
OPTF    = -O3 -fPIC -fopenmp -funroll-loops
OPTL    = -O3 -fPIC -fopenmp -funroll-loops
OPTC    = -O3 -fPIC -fopenmp -funroll-loops
#End Optimized options
INCS = $(INCPAR)
LIBS = $(LIBPAR)
LIBSEQNEEDED =

