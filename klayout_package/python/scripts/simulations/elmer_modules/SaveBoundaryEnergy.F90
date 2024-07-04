 !------------------------------------------------------------------------------
 !  Compile with "elmerf90 SaveBoundaryEnergy.F90 -o obj/SaveBoundaryEnergy"
 !  To check for warnings/debugging also add -fcheck=all -Wall -Wextra -g
 !------------------------------------------------------------------------------
SUBROUTINE SaveBoundaryEnergyComponents(Model,Solver,dt,Transient)
  !------------------------------------------------------------------------------
  USE DefUtils

  IMPLICIT NONE
  !------------------------------------------------------------------------------
  TYPE(Solver_t) :: Solver
  TYPE(Model_t) :: Model
  REAL(KIND=dp) :: dt
  LOGICAL :: Transient
  !------------------------------------------------------------------------------
  TYPE(Variable_t), POINTER :: potvar
  TYPE(Element_t), POINTER :: Element
  INTEGER ::i, Active, iMode, NoModes
  CHARACTER(LEN=MAX_NAME_LEN) :: bc_name !, debug_str
  LOGICAL :: Found
  TYPE(Mesh_t), POINTER :: Mesh
  REAL(KIND=dp), ALLOCATABLE :: IntNorm(:), IntTan(:)
  TYPE(ValueList_t), POINTER :: BC
  CHARACTER(*), PARAMETER :: Caller = 'SaveBoundaryEnergyComponents'

  SAVE IntNorm, IntTan, NoModes
  !-------------------------------------------------------------------------------------------

  CALL Info(Caller,'----------------------------------------------------------',Level=6 )
  CALL Info(Caller,'Computing Boundary energy integrals for normal and tangential components of Electric field',Level=4 )

  Mesh => GetMesh()

  NoModes = Model % NumberOfBCs
  ALLOCATE(IntNorm(NoModes), IntTan(NoModes))


  potvar => VariableGet( Mesh % Variables, 'Potential', ThisOnly = .TRUE.)
  IF(.NOT. ASSOCIATED(potvar) ) THEN
    CALL Fatal(Caller,'Could not find potential!')
  END IF

  IntNorm = 0.0_dp
  IntTan = 0.0_dp

  ! integration
  Active = GetNOFBoundaryElements()
  DO i=1,Active
    Element => GetBoundaryElement(i)

    iMode = GetBCId( Element )
    IF ( iMode > 0 ) THEN
      BC => Model % BCs(iMode) % Values

      IF (.NOT. ASSOCIATED(BC) ) CYCLE

      Found = .FALSE.
      bc_name = ListGetString(BC, 'Boundary Energy Name', Found )

      IF( Found ) THEN
        CALL LocalIntegBC(Element)
      END IF
    END IF
  END DO

  ! parallel sum
  IF( ParEnv % PEs > 1 ) THEN
    DO i=1,Model % NumberOfBCs
      IntNorm(i) = ParallelReduction(IntNorm(i))
      IntTan(i) = ParallelReduction(IntTan(i))
    END DO
  END IF

  ! No permittivity used here. (added in preprocessing)
  IntNorm = 0.5 * IntNorm
  IntTan = 0.5  * IntTan

  ! save data to be used from other solvers
  DO i=1,Model % NumberOfBCs
    BC => Model % BCs(i) % Values

    IF (.NOT. ASSOCIATED(BC) ) CYCLE

    Found = .FALSE.
    bc_name = ListGetString(BC,'Boundary Energy Name', Found )
    IF( Found ) THEN
      ! Make data available for SaveData / SaveScalars solver
      CALL ListAddConstReal(GetSimulation(), TRIM(bc_name) // "_norm_component", IntNorm(i))
      CALL ListAddConstReal(GetSimulation(), TRIM(bc_name) // "_tan_component", IntTan(i))
    END IF
  END DO

CONTAINS
  !-----------------------------------------------------------------------------
  SUBROUTINE LocalIntegBC(Element)
    !------------------------------------------------------------------------------
    TYPE(Element_t), POINTER :: Element
    !------------------------------------------------------------------------------
    REAL(KIND=dp) :: e_ip_norm, e_ip_tan(3), e_ip(3), e_ip_r(3), e_ip_l(3)
    REAL(KIND=dp), ALLOCATABLE :: Basis(:)
    REAL(KIND=dp) :: weight, DetJ, Normal(3), uvw(3) ! Grad(3)
    LOGICAL :: Stat, Found, E_R_zero, E_L_zero
    TYPE(GaussIntegrationPoints_t) :: IP
    INTEGER :: t, m,  n, No
    TYPE(Nodes_t), SAVE :: Nodes
    LOGICAL :: AllocationsDone = .FALSE.
    TYPE(Nodes_t) :: ParentNodesR, ParentNodesL
    TYPE(Element_t), POINTER :: ParentElementR, ParentElementL, Parent
    TYPE(ValueList_t), POINTER :: ParentMaterialR, ParentMaterialL
    REAL(KIND=dp) :: epsr_R, epsr_L
    SAVE AllocationsDone,  Basis
    REAL(KIND=dp), PARAMETER :: zero_threshold = 1e-25 ! TODO find a good threshold

    IF(.NOT. AllocationsDone ) THEN
      m = Mesh % MaxElementDOFs
      ALLOCATE( Basis(m) )
      AllocationsDone = .TRUE.
    END IF

    ParentElementR => Element % BoundaryInfo % Right
    ParentElementL => Element % BoundaryInfo % Left

    IF (.NOT. (ASSOCIATED(ParentElementR) .OR. ASSOCIATED(ParentElementL))) THEN
      CALL FATAL(Caller, 'Neither parent Element was found')
    END IF

    CALL GetElementNodes( Nodes, Element )
    n = Element % TYPE % NumberOfNodes

    Normal = NormalVector(Element, Nodes, Check=.TRUE.)
    IP = GaussPoints(Element)

    ! Choose the Parent element based on first integration point
    t = 1
    stat = ElementInfo( Element, Nodes, IP % U(t), IP % V(t), &
    IP % W(t), detJ, Basis)
    uvw(1)=IP % U(t)
    uvw(2)=IP % V(t)
    uvw(3)=IP % W(t)
    E_R_zero = .True.
    E_L_zero = .True.
    IF ( ASSOCIATED(ParentElementR) ) THEN
      No = 0
      CALL EvaluateVariableAtGivenPoint(No, e_ip_r, Mesh, potvar, Element=Element, LocalCoord=uvw, &
        DoGrad=.TRUE., LocalBasis=Basis, Parent=ParentElementR)
      IF ( No /= 3 ) THEN
        CALL FATAL(Caller, 'Did not find Efield R (No /= 3)')
      ELSE
        E_R_zero = SUM(ABS(e_ip_r)) < zero_threshold
      END IF
    END IF

    IF ( ASSOCIATED(ParentElementL) ) THEN
      No = 0
      CALL EvaluateVariableAtGivenPoint(No, e_ip_l, Mesh, potvar, Element=Element, LocalCoord=uvw, &
        DoGrad=.TRUE., LocalBasis=Basis, Parent=ParentElementL)
      IF ( No /= 3 ) THEN
        CALL FATAL(Caller, 'Did not find Efield L (No /= 3)')
      ELSE
        E_L_zero = SUM(ABS(e_ip_l)) < zero_threshold
      END IF
    END IF

    IF ( E_R_zero ) THEN
      IF ( E_L_zero ) THEN
        ! shouldnt matter which one
        Parent => ParentElementR
      ELSE
        ! choose E_L
        ! WRITE(6,*) 'Choose L based on E'
        Parent => ParentElementL
      END IF
    ELSE
      IF ( E_L_zero ) THEN
        ! choose E_R
        ! WRITE(6,*) 'Choose R based on E'
        Parent => ParentElementR
      ELSE

        ! Both sides have nonzero field
        ! => Choose based on the permittivities of the bodies
        CALL GetElementNodes( ParentNodesR, ParentElementR )
        CALL GetElementNodes( ParentNodesL, ParentElementL )
    
        ParentMaterialR => GetMaterial(ParentElementR)
        ParentMaterialL => GetMaterial(ParentElementL)
    
        Found = .FALSE.
        epsr_R = GetConstReal(ParentMaterialR,'Relative Permittivity', Found)
        IF (.NOT. FOUND) THEN
          CALL FATAL(Caller, 'Did not find R parent permittivity')
        END IF
    
        Found = .FALSE.
        epsr_L = GetConstReal(ParentMaterialL,'Relative Permittivity', Found)
        IF (.NOT. FOUND) THEN
          CALL FATAL(Caller, 'Did not find L parent permittivity')
        END IF
        ! WRITE(6,*) 'PERMITTIVITIES: ', epsr_R, ' ', epsr_L
        IF ( abs(epsr_R - epsr_L) < zero_threshold) THEN
          ! If for some reason the sides have same permittivity choose the one with higher field
          IF (SUM(ABS(e_ip_r)) > SUM(ABS(e_ip_l))) THEN
            ! WRITE(6,*) 'Choose R based on field strength'
            Parent => ParentElementR
          ELSE
            ! WRITE(6,*) 'Choose L based on field strength'
            Parent => ParentElementL
          END IF
        ELSE
          ! choose the side with HIGHER permittivity
          IF (epsr_R > epsr_L) THEN
            Parent => ParentElementR
            ! WRITE(6,*) 'Choose R based on permittivity'
          ELSE 
            ! WRITE(6,*) 'Choose L based on permittivity'
            Parent => ParentElementL
          END IF
        END IF
      END IF
    END IF


    ! Numerical integration:
    !-----------------------
    DO t=1,IP % n
      stat = ElementInfo( Element, Nodes, IP % U(t), IP % V(t), &
        IP % W(t), detJ, Basis)
      weight = IP % s(t) * detJ

      uvw(1)=IP % U(t)
      uvw(2)=IP % V(t)
      uvw(3)=IP % W(t)
      No = 0
      CALL EvaluateVariableAtGivenPoint(No, e_ip, Mesh, potvar, Element=Element, LocalCoord=uvw, &
                                         DoGrad=.TRUE., LocalBasis=Basis, Parent=Parent)

      e_ip_norm = SUM(e_ip*Normal)
      e_ip_tan = e_ip - e_ip_norm * Normal

      IntNorm(iMode) = IntNorm(iMode) + weight * e_ip_norm*e_ip_norm
      IntTan(iMode) = IntTan(iMode) + weight * SUM(e_ip_tan*e_ip_tan)
    END DO

    !------------------------------------------------------------------------------
  END SUBROUTINE LocalIntegBC
  !------------------------------------------------------------------------------
  !------------------------------------------------------------------------
END SUBROUTINE SaveBoundaryEnergyComponents
 !------------------------------------------------------------------------

